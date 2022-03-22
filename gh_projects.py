__version__ = "0.0.1"


import requests
import os
import jq

API_ENDPOINT = "https://api.github.com/graphql"


# API -------------------------------------------------------------------------


class GithubApiSession:
    """Query the github graphql API, with support for pagination."""

    def __init__(self, github_token=None, api_endpoint=API_ENDPOINT):
        """Initialize a github graphql API session.

        Args:
            github_token: a github api token. If none, taken from GITHUB_TOKEN env var.
            api_endpoint: url for the github graphql api endpoint.

        """

        self.session = requests.Session()
        self.api_endpoint = api_endpoint

        github_token = (
            os.environ["GITHUB_TOKEN"] if github_token is None else github_token
        )
        self.session.headers.update({"Authorization": f"token {github_token}"})

    def query(self, q, **kwargs):
        """Execute a graphql query."""
        r = self.session.post(self.api_endpoint, json=dict(query=q, variables=kwargs))

        return r.json()

    def paginated_query(
        self,
        q,
        next_key,
        next_check_key,
        start_cursor=None,
        variables=None,
        cursor_variable="nextCursor",
    ):
        """Execute a graphql query that involves pagination. Return all results."""

        variables = {} if variables is None else variables

        all_results = []

        next_cursor = start_cursor
        has_next_page = True
        while has_next_page:
            raw_data = self.query(q, **variables, **{cursor_variable: next_cursor})
            self.validate_query_result(raw_data)

            data = raw_data["data"]

            all_results.append(data)

            next_cursor = self._extract_path(next_key, data)
            has_next_page = self._extract_path(next_check_key, data)

        return all_results

    @staticmethod
    def validate_query_result(data):
        """Validate whether graphql query was successful."""
        if data.get("errors"):
            raise ValueError(str(data))

    @staticmethod
    def _extract_path(p, data):
        entry = data
        for attr_name in p.split("."):
            entry = entry[attr_name]

        return entry


# Actions ---------------------------------------------------------------------


def fetch_all_issues(owner, repo, issue_attrs=tuple):
    """Fetch all issues for a github repository."""

    issue_attrs_gql = "\n".join(issue_attrs)

    q = (
        """
    query($nextCursor: String, $owner: String!, $repo: String!) {
        repository(name: $repo, owner: $owner) {
          issues(first: 100, after: $nextCursor) {
          nodes {
              id """
        + issue_attrs_gql
        + """
          }
          pageInfo {
              endCursor
              startCursor
              hasNextPage
              hasPreviousPage
          }
          }
        }
    }
    """
    )

    gh = GithubApiSession()

    data = gh.paginated_query(
        q,
        next_key="repository.issues.pageInfo.endCursor",
        next_check_key="repository.issues.pageInfo.hasNextPage",
        variables=dict(owner=owner, repo=repo),
    )

    return jq.compile(".[] | .repository.issues.nodes[]").input(data).all()


def fetch_all_issue_ids(owner, repo):
    """Return a list of ids for all issues in a github repository."""

    data = fetch_all_issues(owner, repo)

    return jq.compile(".[] | .id").input(data).all()


def push_issues_to_project_next(project_id: str, issues: list[str]):
    """Copy issues into a project beta board.

    Args:
        project_id: ID corresponding to the project board.
        issues: list of issue ids to copy.

    """

    q = """
    mutation($projectId:ID!, $contentId:ID!) {
      addProjectNextItem(
        input: {
          projectId: $projectId
          contentId: $contentId
        }
      ) {
        projectNextItem {
          id
        }
      }
    }
    """

    gh = GithubApiSession()

    all_results = []
    for content_id in issues:
        res = gh.query(q, projectId=project_id, contentId=content_id)
        gh.validate_query_result(res)

        all_results.append(res)

    return all_results


def _generate_field_mutation(n_fields):
    field_tmpl = """
      field{ii}: updateProjectNextItemField(
        input: {{
          projectId: $projectId
          itemId: $contentId
          fieldId: $field{ii}
          value: $value{ii}
        }}
      ) {{
        projectNextItem {{
          id
        }}
      }}
    """

    field_args = [f"field{ii}:ID" for ii in range(n_fields)]
    value_args = [f"value{ii}:String!" for ii in range(n_fields)]

    arg_names = [f"${x}" for x in [*field_args, *value_args]]
    signature_args = ", ".join(arg_names)
    actions = "\n\n".join(field_tmpl.format(ii=ii) for ii in range(n_fields))

    return signature_args, actions


def update_project_item_fields(project_id, content_id, fields: dict):
    """Update the fields for a specific project (beta) item."""

    sig_pars, actions = _generate_field_mutation(len(fields))

    q = (
        "mutation($projectId:ID!, $contentId:ID!, "
        + sig_pars
        + ") {\n"
        + actions
        + "\n}"
    )

    gh = GithubApiSession()

    all_field_args = {}
    for ii, (k, v) in enumerate(fields.items()):
        v_or_empty = v if v is not None else ""
        all_field_args.update({f"field{ii}": k, f"value{ii}": v_or_empty})

    res = gh.query(q, projectId=project_id, contentId=content_id, **all_field_args)

    gh.validate_query_result(res)

    return res


def fetch_project_item_fields(project_id):
    """Return all fields (column types) for a specific project."""

    q = """
    query($projectId:ID!) {
      node(id: $projectId) {
        ... on ProjectNext {
          fields(first: 20) {
            nodes {
              id
              name
              settings
            }
          }
        }
      }

    }
    """

    gh = GithubApiSession()

    res = gh.query(q, projectId=project_id)
    gh.validate_query_result(res)

    return jq.compile(".data.node.fields.nodes[]").input(res).all()


def _jq_to_gql(path):
    tree = path.split(".")
    return "{".join(tree) + "}" * (len(tree) - 1)


def fetch_project_item_issue_ids(project_id):
    """Fetch all underlying issue ids (i.e. content ids) for items in a project."""

    q = """
    query($nextCursor:String, $projectId:ID!) {
      node(id: $projectId) {
        ... on ProjectNext {
          items(first: 100, after: $nextCursor) {
            nodes {
              id
              content {
                ... on Issue {
                  id
                }
              }
            }
            pageInfo {
                endCursor
                startCursor
                hasNextPage
                hasPreviousPage
            }
          }
        }
      }

    }
    """

    gh = GithubApiSession()
    data = gh.paginated_query(
        q,
        next_key="node.items.pageInfo.endCursor",
        next_check_key="node.items.pageInfo.hasNextPage",
        variables=dict(projectId=project_id),
    )

    return (
        jq.compile(".[] | .node.items.nodes[] | {item_id: .id, issue_id: .content.id}")
        .input(data)
        .all()
    )


# for each attr need to know issue attr path, project field title (or id)
def update_project_with_repo_issues(
    owner, repo, project_id, issue_attrs, query_fragment
):
    """Update items in a project board, based on their issue attributes.

    Args:
        issue_attrs: mapping of form path_to_issue_attr: field_title. Note that
            the path to an attribute may have form attr.subattr.subsubattr.
    """

    if len(set(issue_attrs.values())) > len(issue_attrs):
        raise ValueError("issue_attrs field ids must be unique")

    # fetch all necessary attributes from issues
    data = fetch_all_issues(owner, repo, [query_fragment])

    # fetch all project fields
    # project_fields = fetch_project_item_fields(project_id)

    rows = []
    for issue in data:
        row = {}
        for path, field_id in issue_attrs.items():
            entries = jq.compile(path).input(issue).all()
            entry = entries[0] if len(entries) else None

            row[field_id] = str(entry) if entry is not None else entry

        rows.append(row)

    issue_ids = jq.compile(".[] | .id").input(data).all()

    # sanity check
    assert len(rows) == len(issue_ids)

    # call update project item fields (mapping field key: attribute value
    all_ids = fetch_project_item_issue_ids(project_id)
    issue_id_to_item = {entry["issue_id"]: entry["item_id"] for entry in all_ids}
    item_ids = [issue_id_to_item[issue_id] for issue_id in issue_ids]

    # res = push_issues_to_project_next(project_id, issue_ids)

    all_results = []
    for project_item_id, row in zip(item_ids, rows):
        res = update_project_item_fields(project_id, project_item_id, row)
        all_results.append(res)

    return all_results


# from gh_projects import fetch_project_item_fields
# fetch_project_item_fields("PN_kwHOACdIos4AAYbQ")

# update_project_item_fields
