import jq

from dotenv import load_dotenv
from gh_projects import (
    update_project_with_repo_issues,
    fetch_all_issues,
    push_issues_to_project_next,
)


load_dotenv()

PROJECT_ID = "PN_kwHOACdIos4AAto7"

# fetch_project_item_issue_ids("PN_kwHOACdIos4AAYbQ")

all_issues = fetch_all_issues("machow", "pins-python", ["projectNext(number: 1) { id }"])
need_project = (
    jq.compile(".[] | select(.projectNext.id == null) | .id").input(all_issues).all()
)

push_issues_to_project_next(PROJECT_ID, need_project)


update_project_with_repo_issues(
    "machow",
    "pins-python",
    PROJECT_ID,
    {
        ".updatedAt": "MDE2OlByb2plY3ROZXh0RmllbGQyNjI0ODEw",
        ".createdAt": "MDE2OlByb2plY3ROZXh0RmllbGQyNjI0ODM4",
        ".closedAt": "MDE2OlByb2plY3ROZXh0RmllbGQyNjI0ODM5",
        ".author.login": "MDE2OlByb2plY3ROZXh0RmllbGQyNjI0ODQ5",
        ".comments.totalCount": "MDE2OlByb2plY3ROZXh0RmllbGQyNjI0ODk4",
        ".comments.nodes[] | .createdAt": "MDE2OlByb2plY3ROZXh0RmllbGQyNjI0ODk3",
        ".comments.nodes[] | .author.login": "MDE2OlByb2plY3ROZXh0RmllbGQyNjI0ODg3",
        ".isReadByViewer": "MDE2OlByb2plY3ROZXh0RmllbGQyNjI0ODc3",
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
