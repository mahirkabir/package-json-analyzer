import requests
from bs4 import BeautifulSoup, SoupStrainer
import constants
import re
from git_helper import GitHelper
import os
from datetime import datetime
import time

# checks if the project has
# 1. valid github url for node-js project [input url is npm site url]
# 2. dependencies tag
# 3. valid build script
# 4. no packag-lock file


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
            status = helper.get_repo_status(repo_url)
            return [status["result"], repo_url, status]
    except Exception as ex:
        return [False]


def log_repos(repos, path):
    fout = open(path, "w")
    for repo in repos:
        fout.write(repo[0] + "\t" + repo[1])
        fout.write("\n")
    fout.close()


if __name__ == "__main__":

    most_dependent_upon = "https://gist.githubusercontent.com/anvaka/8e8fa57c7ee1350e3491/raw/b6f3ebeb34c53775eea00b489a0cea2edd9ee49c/01.most-dependent-upon.md"

    page = requests.get(most_dependent_upon)

    if(page.status_code == constants.ERROR_CODE_NOT_FOUND):
        print("Page not found")
    else:
        ts = datetime.now()

        soup = BeautifulSoup(page.content, "html.parser")

        repositories = re.findall("\d+\. \[(.+)\]\((.+)\)", soup.text)

        all_repos = []
        ok_repos = []
        package_lock_repos = []
        no_dependencies_repos = []
        no_build_script_repos = []
        not_node_js_repos = []

        processed_cnt = 0
        for repo in repositories:
            processed_cnt += 1

            if((processed_cnt) % 100 == 0):
                # for each 50 repos delaying 5 mins (5 * 60 = 300s to avoid request timeout)
                time.sleep(300)

            try:
                # group 0=> repo name, group 1=> url
                result = is_ok_to_process(
                    repo[0], repo[1], ["dependencies", "devDependencies"])

                if len(result) == 1:
                    print("Exception occurred for: " + repo[0])
                else:
                    # result: [0] = ok or not, [1] = git url, [2] = status
                    repo_name = repo[0]
                    repo_url = result[1]

                    all_repos.append([repo_name, repo_url])

                    if(result[0]):
                        ok_repos.append([repo_name, repo_url])
                    elif(result[2]["node-js"]):
                        if(result[2]["package-lock"]):
                            package_lock_repos.append([repo_name, repo_url])

                        if(not result[2]["dependencies"]):
                            no_dependencies_repos.append([repo_name, repo_url])

                        if(not result[2]["build-scripts"]):
                            no_build_script_repos.append([repo_name, repo_url])
                    else:
                        not_node_js_repos.append([repo_name, repo_url])
            except Exception as ex:
                print("Exception occurred for: " + repo[0])

        log_folder = os.path.join("data", "npm_rank")

        log_repos(all_repos, os.path.join(log_folder, "npm_rank.txt"))
        log_repos(ok_repos, os.path.join(
            log_folder, "npm_rank_ok.txt"))
        log_repos(package_lock_repos, os.path.join(
            log_folder, "npm_rank_package_lock.txt"))
        log_repos(no_dependencies_repos, os.path.join(
            log_folder, "npm_rank_no_dependencies.txt"))
        log_repos(no_build_script_repos, os.path.join(
            log_folder, "npm_rank_no_build_script.txt"))
        log_repos(not_node_js_repos, os.path.join(
            log_folder, "npm_rank_not_node_js.txt"))

        te = datetime.now()

        print("-------------------------------")
        print("Process completed. Time: " + str(te - ts))
        print("# of Total OK repositories: " + str(len(ok_repos)))
        print("# of Total found repositories: " + str(len(all_repos)))
        print("# of repositories having package-lock.json: " +
              str(len(package_lock_repos)))
        print("# of repositories missing dependencies: " +
              str(len(no_dependencies_repos)))
        print("# of repositories missing build script: " +
              str(len(no_build_script_repos)))
        print("# of repositories that are not for node-js: " +
              str(len(not_node_js_repos)))
        print("-------------------------------")
