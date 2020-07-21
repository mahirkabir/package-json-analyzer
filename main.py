import os
import json
import subprocess
import semantic_version

libraries = []
dict_lib_versions = {}

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

    return allowed_versions


def parse_json(str_json):
    return json.loads(str_json)


def get_dependencies(str_package_json, dependency_type="dependencies"):
    parsed_package_json = parse_json(str_package_json)
    dict_dependencies = parsed_package_json[dependency_type]

    for pair_lib in dict_dependencies:
        pair_ver = dict_dependencies[pair_lib]
        try:
            libraries.append(pair_lib)
            dict_lib_versions[pair_lib] = get_allowed_versions(
                pair_lib, pair_ver)

        except Exception as e:
            print("Error occurred for: {library} => {e}".format(
                library=pair_lib, e=e))


def readPackageJSON(path):
    content = ""
    f_json = open(path, "r")
    content = f_json.read()
    f_json.close()
    return content


# ------------------------------------------
# Updates package.json using global libraries & dict_lib_versions
# ------------------------------------------
def updatePackageJSON(path, dependency_type="dependencies"):
    f_json = open(path, "r")
    package_json = json.load(f_json)
    f_json.close()

    for library in libraries:
        lib_versions = dict_lib_versions.get(library)
        package_json[dependency_type][library] = lib_versions[0]

    f_json = open(path, "w")
    json.dump(package_json, f_json)
    f_json.close()


if __name__ == "__main__":
    package_json = readPackageJSON("package.json")

    get_dependencies(package_json)

    updatePackageJSON("package.json")
