import os
import json
import subprocess
import semantic_version
import itertools
from git_helper import GitHelper
import configparser
import constants
import os
import os.path
from db_helper import DBInstance

# ------------------------------------------
# sample input: dict_lib_versions = {'libA': ['vA1', 'vA2', 'vA3'],
#                         'libB': ['vB1', 'vB2', 'vB3'],
#                         'libC': ['vC1', 'vC2', 'vC3']}
# sample output => [('vA1', 'vB1', 'vC1'), ('vA1', 'vB1', 'vC2'), ('vA1', 'vB1', 'vC3'), ('vA1', 'vB2', 'vC1'), ('vA1', 'vB2', 'vC2'), ('vA1', 'vB2', 'vC3'), ('vA1', 'vB3', 'vC1'), ('vA1', 'vB3', 'vC2'), ('vA1', 'vB3', 'vC3'), ('vA2', 'vB1', 'vC1'), ('vA2', 'vB1', 'vC2'), ('vA2', 'vB1', 'vC3'), ('vA2', 'vB2', 'vC1'), ('vA2', 'vB2', 'vC2'), ('vA2', 'vB2', 'vC3'), ('vA2', 'vB3', 'vC1'), ('vA2', 'vB3', 'vC2'), ('vA2', 'vB3', 'vC3'), ('vA3', 'vB1', 'vC1'), ('vA3', 'vB1', 'vC2'), ('vA3', 'vB1', 'vC3'), ('vA3', 'vB2', 'vC1'), ('vA3', 'vB2', 'vC2'), ('vA3', 'vB2', 'vC3'), ('vA3', 'vB3', 'vC1'), ('vA3', 'vB3', 'vC2'), ('vA3', 'vB3', 'vC3')]
# ------------------------------------------


def get_all_lib_combos(dict_lib_versions):
    lst = list(dict_lib_versions.values())
    return list(itertools.product(*lst))

# ------------------------------------------
# sample input: ([<all webpack versions ("0.1.0" .. "5.0.0-beta.22")>], ~1.12.2)
# sample output => "1.12.2, .., 1.12.6, .., 1.12.10, .., 1.12.15"
# ------------------------------------------


def get_allowed_versions_from_all(all_versions, version_rule):

    allowed_versions = []
    rule = semantic_version.SimpleSpec(version_rule)

    for version in all_versions:
        if(semantic_version.Version(version) in rule):
            allowed_versions.append(version)

    return allowed_versions


# ------------------------------------------
# sample input: (webpack, ~1.12.2)
# sample output => "1.12.2, .., 1.12.6, .., 1.12.10, .., 1.12.15"
# ------------------------------------------
def get_allowed_versions(library, version):
    cmd = "npm view {library} versions --json".format(
        library=library)

    out = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)

    stdout, stderr = out.communicate()
    # utf-8 encoding is reverse compatible with ASCII
    str_stdout = stdout.decode("utf-8")
    all_lib_versions = parse_json(str_stdout)

    allowed_versions = get_allowed_versions_from_all(all_lib_versions, version)

    if(len(allowed_versions) == 0):
        allowed_versions.append(version)

    return allowed_versions


def parse_json(str_json):
    return json.loads(str_json)


def get_dependency_names(str_package_json, dependency_type="dependencies"):
    libraries = []

    parsed_package_json = parse_json(str_package_json)

    if(dependency_type in parsed_package_json):
        dict_dependencies = parsed_package_json[dependency_type]

        for pair_lib in dict_dependencies:
            try:
                libraries.append(pair_lib)

            except Exception as e:
                raise Exception("Error occurred for: {library} => {e}".format(
                    library=pair_lib, e=e))

    return libraries

def get_dependencies(str_package_json, dependency_type="dependencies"):
    libraries = []
    dict_lib_versions = {}

    parsed_package_json = parse_json(str_package_json)

    if(dependency_type in parsed_package_json):
        dict_dependencies = parsed_package_json[dependency_type]

        for pair_lib in dict_dependencies:
            pair_ver = dict_dependencies[pair_lib]
            try:
                libraries.append(pair_lib)
                dict_lib_versions[pair_lib] = get_allowed_versions(
                    pair_lib, pair_ver)

            except Exception as e:
                raise Exception("Error occurred for: {library} => {e}".format(
                    library=pair_lib, e=e))

    return [libraries, dict_lib_versions]


def read_package_json(path):
    content = ""
    f_json = open(path, "r")
    content = f_json.read()
    f_json.close()
    return content


# ------------------------------------------
# Updates package.json using global libraries & dict_lib_versions' combination
# dict_lib_type is to find out which library belongs to which dependency type
# ------------------------------------------
def update_package_json(path, libraries, dict_lib_type, lib_combo):
    f_json = open(path, "r")
    package_json = json.load(f_json)
    f_json.close()

    libIdx = 0
    for library in libraries:
        dependency_type = dict_lib_type[library]
        package_json[dependency_type][library] = lib_combo[libIdx]
        libIdx += 1

    f_json = open(path, "w")
    json.dump(package_json, f_json)
    f_json.close()


def execute_cmd(path, cmd):

    working_dir = os.getcwd()
    os.chdir(path)

    out = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)

    stdout, stderr = out.communicate()
    # utf-8 encoding is reverse compatible with ASCII
    str_stdout = stdout.decode("utf-8")

    os.chdir(working_dir)

    if "ERR" in str_stdout or "err" in str_stdout:
        return [False, str_stdout]
    else:
        return [True, str_stdout]


def clone_repo_to_dir(directory, git_url, repo_name):
    repo_safe_name = repo_name
    suffix = 0
    while os.path.exists(os.path.join(directory, repo_safe_name)):
        suffix += 1
        repo_safe_name = repo_name + "_" + str(suffix)

    cmd = "git clone {git_url} {repo_name}".format(
        git_url=git_url, repo_name=repo_safe_name)
    clone_result = execute_cmd(directory, cmd)

    if(clone_result[0] == False):
        raise Exception(clone_result[1])
    else:
        return repo_safe_name


def remove_folder(root, folder):
    folder_to_delete = os.path.join(
        root, folder)

    if(os.path.isdir(folder_to_delete)):
        if not (execute_cmd(folder_to_delete, "DEL /F/Q/S *.* > NUL")[0] and execute_cmd(root, "RMDIR /Q/S " + folder_to_delete)[0]):
            raise Exception("Error removing: " + folder)


def add_combo_repo(db_instance, libraries, combo, url):
    try:
        combo_main_pattern = []

        libIdx = 0
        for library in libraries:
            combo_main_pattern.append(library + "=>" + combo[libIdx])
            libIdx += 1

        combo_str = ", ".join(combo_main_pattern)

        db_instance.add_combo_repo(combo_str, url)

    except Exception as ex:
        print("Error inserting combo-repo_url information: " + str(ex))


def get_npm_rank_repos():
    reader = open("npm_rank.txt", "r")

    repo_lines = reader.readlines()
    npm_rank_repos = []

    for repo_line in repo_lines:
        repo_info = repo_line.split("\t")
        repo = {"name": repo_info[0].strip(), "url": repo_info[1].strip()}
        npm_rank_repos.append(repo)

    reader.close()

    return npm_rank_repos


def get_dict_repo_count():
    reader = open("sorted_libraries.txt", "r")

    repo_lines = reader.readlines()
    dict_repo_count = {}

    for repo_line in repo_lines:
        repo_info = repo_line.split("\t")
        count = repo_info[1].strip()
        dict_repo_count[repo_info[0].strip()] = count

    reader.close()

    return dict_repo_count

# finds out if package-lock.json is there
# finds out if dependencies and devDependencies have overlapping libraries


def collect_info(repo):
    helper = GitHelper()
    repo = {"name": repo["name"], "url": repo["url"], "count": repo["count"],
            "has_package_lock": helper.has_package_lock(repo["url"]), "overlapping_libs": []}

    str_package_json = helper.get_str_package_json(repo["url"])
    # collecting overlapping libraries
    dependencies = get_dependency_names(str_package_json, "dependencies")
    dev_dependencies = get_dependency_names(
        str_package_json, "devDependencies")

    repo["overlapping_libs"] = list(set(dependencies) & set(dev_dependencies))

    return repo

# tracks which library comes from which dependency type
# sample input: ["lodash", "webpack"], "devDependency"
# sample output: {"lodash": "devDependency", "webpack": "devDependency"}


def list_to_dict(libs, dep_type):
    sz = len(libs)
    dict = {libs[i]: dep_type for i in range(0, sz)}
    return dict

if __name__ == "__main__":

    # github = GitHelper("dependencies")
    # repositories = github.get_ok_to_process_repos()

    repositories = get_npm_rank_repos()
    dict_repo_count = get_dict_repo_count()  # has count of # of possible combos
    # TODO: Need to update it, because it is read from file and is not updated automatically

    # keeping only repos having <= 1000 possible combos
    # TODO: Current dataset has no duplicate names, but need to handle it in future to make tool scalable
    repositories = list(filter(lambda repo: repo["name"] in dict_repo_count
                               and int(dict_repo_count[repo["name"]]) <= constants.LIMIT_OF_NO_OF_VALID_COMBO,
                               repositories))

    repositories = list(map(lambda repo: {"name": repo["name"],
                                          "url": repo["url"], "count": int(dict_repo_count[repo["name"]])},
                            repositories))

    # sort them based on their valid combo count
    repositories.sort(key=lambda repo: repo["count"])

    repositories = list(map(lambda repo: collect_info(repo), repositories))

    config = configparser.ConfigParser()
    config.read("config.ini")
    dataset_root = config.get("PATHS", "DATESET_PATH")

    db_config = config["DB CONNECT"]
    password = db_config["PASSWORD"]
    if password == "<BLANK>":
        password = ""

    try:
        db_instance = DBInstance(
            db_config["HOST"], db_config["USER"], password, db_config["DATABASE"])
    except Exception as ex:
        db_instance = ""

    run_stats = {"total": 0, "package-lock": 0, "overlapping": 0}

    for repo in repositories:
        try:
            print("Processing: " + repo["url"])

            run_stats["total"] += 1

            if(repo["has_package_lock"]):
                print(repo["name"] + " has package-lock.json")
                run_stats["package-lock"] += 1

            if len(repo["overlapping_libs"]) > 0:
                print(repo["name"] + " has overlapping libraries: " +
                      ",".join(repo["overlapping_libs"]))
                run_stats["overlapping"] += 1

            if repo["has_package_lock"] == False and len(repo["overlapping_libs"]) == 0:
                repo_name = clone_repo_to_dir(
                    dataset_root, repo["url"], repo["name"])

                try:
                    repo_loc = os.path.join(dataset_root, repo_name)

                    package_json_loc = os.path.join(repo_loc, "package.json")

                    package_json = read_package_json(package_json_loc)

                    libraries = []
                    dict_lib_versions = {}
                    dict_lib_type = {}

                    for dependency_type in ["dependencies", "devDependencies"]:
                        try:
                            result = get_dependencies(
                                package_json, dependency_type)
                            # adding all dependent libraries in list
                            libraries.extend(result[0])
                            # adding all dependencies in dictionary
                            dict_lib_versions.update(result[1])
                            # tracking which lib comes from which type
                            dict_lib_type.update(list_to_dict(
                                result[0], dependency_type))

                        except Exception as ex:
                            pass

                    log_file_loc = os.path.join(
                        "logs", repo_name + ".txt")
                    log = open(log_file_loc, "w")

                    libraries_str = "\t".join(libraries)
                    log.write(libraries_str + "\tReason\n")

                    # mult = 1
                    # for lib in libraries:
                    # mult *= len(dict_lib_versions[lib])
                    # print(mult)

                    library_combos = get_all_lib_combos(
                        dict_lib_versions)
                    for combo in library_combos:

                        if(len(libraries) != len(combo)):
                            raise Exception(
                                "Mismatch in no. of libraries and versions")

                        if db_instance != "":
                            add_combo_repo(
                                db_instance, libraries, combo, repo["url"])
                        else:
                            print("DATABASE CONNECTION FAILED")

                        update_package_json(
                            package_json_loc, libraries, dict_lib_type, combo)

                        project_path = repo_loc

                        npm_install_result = execute_cmd(
                            project_path, "npm install")

                        if(npm_install_result[0]):
                            build_project_result = execute_cmd(
                                project_path, "npm run build")

                            if(build_project_result[0] == False):
                                combo_str = "\t".join(combo)
                                reason = build_project_result[1]
                                reason = reason.replace("\n", "</ br>").replace("\t", "</ TAB>")
                                log.write(combo_str + "\t" + reason + "\n")

                        # removing, even if partially installed
                        remove_folder(project_path, "node_modules")

                    log.close()
                except Exception as ex:
                    raise ex
                
                finally:
                    # removing repo folder after working on it
                    remove_folder(dataset_root, repo_name)
                    print("# of processed repositories so far: " + str(run_stats["total"]))  

        except Exception as ex:
            print("Error processing repository => " + str(ex))

    print("-------------------------------")
    print("Process completed")
    print("# of Total processed repositories: " + str(run_stats["total"]))
    print("# of repositories having package-lock.json: " +
          str(run_stats["package-lock"]))
    print("# of repositories having overlapping libraries in dependencies and devDependencies: " +
          str(run_stats["overlapping"]))
    print("-------------------------------")
