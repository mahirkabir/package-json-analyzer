import pyfpgrowth

transactions = [["webpack=>1.5", "lodash=>1.7"], ["lodash=>1.7", "webpack=>1.5"]]

patterns = pyfpgrowth.find_frequent_patterns(transactions, 1)

print(patterns)

# FOR FUTURE EMPIRICAL STUDIES:
# read all from combination_repo table
# in combination_repo table, the rows will be like: "webpack=>1.5", "lodash=>1.7"||github.com...
# we will have to split them to get combo-arrays like: ["webpack=>1.5", "lodash=>1.7"]
# there will be a parent array for combo-arrays: [["webpack=>1.5", "lodash=>1.7"], ["lodash=>1.7", "webpack=>1.5"]]
# then we need to use pyfpgrowth for finding the count of each combination in projects