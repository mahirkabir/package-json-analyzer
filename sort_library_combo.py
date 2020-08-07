# will sort the precomputed library combo list in descending order to their possible combinations count

dict_lib_counts = {}

def cmp(item):
    return dict_lib_counts[item]

if __name__ == "__main__":

    libraries = []
    
    reader = open("library_combo.txt")
    combo_counts = reader.readlines()
    reader.close()
    
    for combo_count in combo_counts:
        combo_count = combo_count.strip()
        parts = combo_count.split("\t")

        # parts = [lib, # of occurences, type of dependency]
        # according to our logic, # of occs = dependency occs * devDependency occs
        if(parts[0] in dict_lib_counts):
            dict_lib_counts[parts[0]] *= int(parts[1])
        else:
            dict_lib_counts[parts[0]] = int(parts[1])
            libraries.append(parts[0])

    libraries.sort(key=cmp)

    writer = open("sorted_libraries.txt", "w")

    for lib in libraries:
        if(dict_lib_counts[lib] != 1):
            writer.write(lib + "\t" + str(dict_lib_counts[lib]))
            writer.write("\n")
    
    writer.close()