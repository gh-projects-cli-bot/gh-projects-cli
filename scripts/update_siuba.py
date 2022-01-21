import jq

from dotenv import load_dotenv
from gh_projects import (
    update_project_with_repo_issues,
    fetch_all_issues,
    push_issues_to_project_next,
)


load_dotenv()

SIUBA_PROJECT_ID = "PN_kwHOACdIos4AAYbQ"

# fetch_project_item_issue_ids("PN_kwHOACdIos4AAYbQ")

all_issues = fetch_all_issues("machow", "siuba", ["projectNext(number: 1) { id }"])
need_project = (
    jq.compile(".[] | select(.projectNext.id == null) | .id").input(all_issues).all()
)

push_issues_to_project_next(SIUBA_PROJECT_ID, need_project)


update_project_with_repo_issues(
    "machow",
    "siuba",
    SIUBA_PROJECT_ID,
    {
        ".updatedAt": "MDE2OlByb2plY3ROZXh0RmllbGQxMDM1NTE1",
        ".createdAt": "MDE2OlByb2plY3ROZXh0RmllbGQxMDM1NTE0",
        ".closedAt": "MDE2OlByb2plY3ROZXh0RmllbGQxMDUwNDQ4",
        ".author.login": "MDE2OlByb2plY3ROZXh0RmllbGQxMDUwNTI2",
        ".comments.totalCount": "MDE2OlByb2plY3ROZXh0RmllbGQxMDM1NTQy",
        ".comments.nodes[] | .createdAt": "MDE2OlByb2plY3ROZXh0RmllbGQxMDUzNDgy",
        ".comments.nodes[] | .author.login": "MDE2OlByb2plY3ROZXh0RmllbGQxMDgyMzkw",
        ".isReadByViewer": "MDE2OlByb2plY3ROZXh0RmllbGQxMDgzNTA4",
    },
    query_fragment="""
      updatedAt
      createdAt
      closedAt
      author { login }
      isReadByViewer
      comments(last: 1) {
        totalCount
        nodes {
          createdAt
          author {
            login
          }
        }
      }
    """,
)
