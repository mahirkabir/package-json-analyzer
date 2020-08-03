import mysql.connector


class DBInstance:
    def __init__(self, host, user, password, dbname):
        self.dbInstance = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=dbname
        )

    def add_combo_repo(self, combination, repo_url):
        cursor = self.dbInstance.cursor()

        sql = '''
            INSERT INTO combination_repo(combination, repo_url)
            VALUE ('{combination}', '{repo_url}')
        '''.format(combination=combination,
                   repo_url=repo_url)

        cursor.execute(sql)
        self.dbInstance.commit()
