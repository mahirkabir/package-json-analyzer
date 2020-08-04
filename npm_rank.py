import requests
from bs4 import BeautifulSoup, SoupStrainer
import constants
import re
from git_helper import GitHelper

# checks if the project has
# 1. valid github url [input url is npm site url]
# 2. dependencies tag
# 3. valid build script


def is_ok_to_process(repo, url, dependency_types):
    page = requests.get(url)

    if(page.status_code == constants.ERROR_CODE_NOT_FOUND):
        return False

    soup = BeautifulSoup(page.content, "html.parser")

    repository_div = ""
    for elem in soup(text="Repository"):
        try:
            repository_div = elem.parent.parent  # there should be only one
        except:
            repository_div = ""

    try:
        repo_url = repository_div.find("a")["href"]
        if "github.com" in repo_url:
            helper = GitHelper(dependency_types)
            if(helper.ok_to_process(repo_url)):
                return [True, repo_url]
    except Exception as ex:
        return [False]

    return [False]


if __name__ == "__main__":

    # ok_to_process_repos = []

    most_dependent_upon = "https://gist.githubusercontent.com/anvaka/8e8fa57c7ee1350e3491/raw/b6f3ebeb34c53775eea00b489a0cea2edd9ee49c/01.most-dependent-upon.md"

    page = requests.get(most_dependent_upon)

    if(page.status_code == constants.ERROR_CODE_NOT_FOUND):
        print("Page not found")
    else:
        soup = BeautifulSoup(page.content, "html.parser")

        repositories = re.findall("\d+\. \[(.+)\]\((.+)\)", soup.text)

        fout = open("npm_rank.txt", "w")

        for repo in repositories:
            # group 0=> repo name, group 1=> url
            result = is_ok_to_process(repo[0], repo[1], ["dependencies", "devDependencies"])
            if(result[0]):
                # result[1] contains the git url of the repo
                # ok_to_process_repos.append([repo[0], result[1]])
                fout.write(repo[0] + "\t" + result[1])
                fout.write("\n")
            
        fout.close()

