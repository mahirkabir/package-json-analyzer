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


def get_dependencies(str_package_json, dependency_type="dependencies"):
    parsed_package_json = parse_json(str_package_json)
    dict_dependencies = parsed_package_json[dependency_type]

    libraries = []
    dict_lib_versions = {}

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


def readPackageJSON(path):
    content = ""
    f_json = open(path, "r")
    content = f_json.read()
    f_json.close()
    return content


# ------------------------------------------
# Updates package.json using global libraries & dict_lib_versions' combination
# ------------------------------------------
def updatePackageJSON(path, libraries, lib_combo, dependency_type="dependencies"):
    f_json = open(path, "r")
    package_json = json.load(f_json)
    f_json.close()

    libIdx = 0
    for library in libraries:
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


def clone_repo_to_dir(directory, git_url):
    clone_result = execute_cmd(directory, "git clone " + git_url)

    if(clone_result[0] == False):
        raise Exception(clone_result[1])


if __name__ == "__main__":
    github = GitHelper("dependencies")
    repositories = github.get_ok_to_process_repos()

    config = configparser.ConfigParser()
    config.read("config.ini")
    dataset_root = config.get("PATHS", "DATESET_PATH")

    for repo in repositories:
        try:
            clone_repo_to_dir(dataset_root, repo["git_url"])

            repo_loc = os.path.join(dataset_root, repo["name"])

            package_json_loc = os.path.join(repo_loc, "package.json")

            package_json = readPackageJSON(package_json_loc)

            result = get_dependencies(package_json)
            libraries = result[0]
            dict_lib_versions = result[1]

            log_file_loc = os.path.join("logs", repo["name"] + ".txt")
            log = open(log_file_loc, "w")

            log.write("\t".join(libraries) + "\n")
            library_combos = get_all_lib_combos(dict_lib_versions)
            for combo in library_combos:
                if(len(libraries) != len(combo)):
                    raise Exception(
                        "Mismatch in no. of libraries and versions")

                updatePackageJSON(package_json_loc, libraries, combo)

                project_path = repo_loc

                npm_install_result = execute_cmd(project_path, "npm install")

                if(npm_install_result[0]):
                    build_project_result = execute_cmd(
                        project_path, "npm run build")

                    # if(build_project_result[0] == False):
                    log.write("\t".join(combo) + "\n")

                    node_modules_dir = os.path.join(
                        project_path, "node_modules")

                    if not (execute_cmd(node_modules_dir, "DEL /F/Q/S *.* > NUL")[0] and execute_cmd(project_path, "RMDIR /Q/S node_modules")[0]):
                        raise Exception("Error cleaning installed packages")

                break

            break

        except Exception as ex:
            print("Error processing repository => " + str(ex))
