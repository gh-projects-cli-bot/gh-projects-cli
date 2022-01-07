import requests
import os
import jq

API_ENDPOINT="https://api.github.com/graphql"


# API -------------------------------------------------------------------------

class GithubApiSession:
    def __init__(self, github_token=None, api_endpoint=API_ENDPOINT):
        self.session = requests.Session()
        self.api_endpoint = api_endpoint

        github_token = os.environ["GITHUB_TOKEN"] if github_token is None else github_token
        self.session.headers.update(
            {"Authorization": f"token {github_token}"}
        )

    def query(self, q, **kwargs):
        print(kwargs)
        r = self.session.post(
            self.api_endpoint,
            json=dict(query=q, variables=kwargs)
        )

        return r.json()

    def paginated_query(
            self,
            q,
            next_key,
            next_check_key,
            start_cursor=None,
            variables=None,
            cursor_variable="nextCursor"
            ):

        variables = {} if variables is None else variables

        all_results = []

        next_cursor = start_cursor
        has_next_page = True
        while has_next_page:
            raw_data = self.query(q, **variables, **{cursor_variable: next_cursor})

            data = raw_data["data"]

            all_results.append(data)

            next_cursor = self.extract_path(next_key, data)
            has_next_page = self.extract_path(next_check_key, data)

        return all_results

    @staticmethod
    def validate_query_result(data):
        if data.get("errors"):
            raise ValueError(str(data))

    @staticmethod
    def extract_path(p, data):
        entry = data
        for attr_name in p.split("."):
            entry = entry[attr_name]

        return entry


# Actions ---------------------------------------------------------------------

def fetch_all_issues(owner, repo):
    q = """
    query($nextCursor: String, $owner: String!, $repo: String!) {
        repository(name: $repo, owner: $owner) {
          issues(first: 100, after: $nextCursor) {
          nodes {
              id
              number
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

    gh = GithubApiSession()

    data = gh.paginated_query(
        q,
        next_key="repository.issues.pageInfo.endCursor",
        next_check_key="repository.issues.pageInfo.hasNextPage",
        variables=dict(owner=owner, repo=repo)
    )

    return jq.compile(".[] | .repository.issues.nodes[] | .id").input(data).all()


def push_issues_to_project_next(project_id, issues: list):
    q = """
    mutation($projectId:String!, $contentId:String!) {
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




