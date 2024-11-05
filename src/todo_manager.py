import mysql.connector
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate
import json

def get_db_connection():
    with open('config.json','r') as f:
        config = json.load(f)

    connection = mysql.connector.connect(
        host='localhost',
        user=config['user'],
        password=config['password'],
        database='TODO_MANAGER'
    )
    return connection  


def add_task():
    connection = get_db_connection()
    cursor = connection.cursor()

    description = input("Enter Description: ")
    days_due = int(input("Due in how many days (e.g., 4, 5, 6): "))
    due_date = datetime.now() + timedelta(days=days_due)

    cursor.execute("INSERT INTO TASKS (description, due_date) VALUES (%s, %s)", 
                   (description, due_date))
    connection.commit()
    print("Task added successfully!")

    connection.close()


def delete_task(task_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM TASKS WHERE id = %s", (task_id,))
    connection.commit()

    print(f"Task {task_id} deleted successfully!")

    connection.close()


def mark_done(task_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("UPDATE TASKS SET task_completed_at = NOW() WHERE id = %s", (task_id,))
    connection.commit()

    print(f"Task {task_id} marked as done!")

    connection.close()


def list_task(only_complete, only_due, last_n_days):
    connection = get_db_connection()
    cursor = connection.cursor()


    query = """
        SELECT T.id, T.description, T.due_date, T.task_created_at, T.task_completed_at,GROUP_CONCAT(C.comment SEPARATOR '|') AS comments
        FROM TASKS T
        LEFT JOIN COMMENTS C ON T.id = C.task_id
        GROUP BY T.id, T.description, T.due_date, T.task_created_at, T.task_completed_at
        """
    where_query_list = []
    if only_complete:
        where_query_list.append("T.task_completed_at IS NOT NULL")
        # query = base_query + " WHERE task_completed_at IS NOT NULL"
    elif only_due:
        where_query_list.append("T.task_completed_at IS NULL")
        # query = base_query + " WHERE task_completed_at IS NULL"
    if last_n_days is not None:
        where_query_list.append(f"T.task_created_at >= NOW() - INTERVAL {last_n_days} DAY")
        # query = base_query + f" WHERE task_created_at >= NOW() - INTERVAL {last_n_days} DAY"
    # else:
    #     query = base_query


    if where_query_list:
        joined_where_clause = " AND ".join(where_query_list)
        where_clause = f" WHERE {joined_where_clause}"
        query = query + where_clause


    cursor.execute(query)
    results = cursor.fetchall()
    # import pdb;pdb.set_trace()

    format_results = []
    for row in results:
        id,description,due_date,task_created_at,task_completed_at,comments= row 

        days_due_elapsed =(datetime.now() - due_date).days
        days_since_created =(datetime.now() - task_created_at).days


        created_at_str = f"{task_created_at} ({days_since_created} days)"

        format_results.append([id, description, days_due_elapsed, created_at_str, task_completed_at,comments])
        

    header = ["id", "Description","Days Due Elapsed", "Days Since Created(days)", "Task Completed At","Comment"]

    print(tabulate(format_results, headers=header, tablefmt="grid",numalign="center"))

    connection.close()

def task_report(last_n_days):
    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
    SELECT 
        COUNT(*) AS total_tasks,
        SUM(CASE WHEN task_completed_at IS NOT NULL AND due_date >= NOW() THEN 1 ELSE 0 END) AS completed_on_time,
        SUM(CASE WHEN task_completed_at IS NOT NULL AND due_date < NOW() THEN 1 ELSE 0 END) AS completed_past_due,
        SUM(CASE WHEN task_completed_at IS NULL AND due_date >= NOW() THEN 1 ELSE 0 END) AS to_be_completed
    FROM TASKS
    """

    where_query_list = []

    if last_n_days is not None:
        where_query_list.append(f"task_created_at >= NOW() - INTERVAL {last_n_days} DAY")

    if where_query_list:
        joined_where_clause =" AND ".join(where_query_list) 
        where_clause = f" WHERE {joined_where_clause}"
        query = query + where_clause

    cursor.execute(query)
    result = cursor.fetchone()

    headers = ["Totat Number Of Tasks","Tasks Completed On Time","Task Completed Past Due","Task To Be Completed"]

    data = [result]  

    print("Report :")

    print(tabulate(data,headers = headers,tablefmt ="grid",numalign="center")) 

    connection.close() 


def add_comment(task_id):
    connection = get_db_connection()

    cursor = connection.cursor()

    comment = input("Enter Your Comment(Press Enter To Leave It Blank):")

    cursor.execute("INSERT INTO COMMENTS (task_id, comment) VALUES (%s, %s)", (task_id, comment))

    connection.commit()

    print(f"Comment added to task {task_id} successfully!")

    connection.close()


def main():
    parser = argparse.ArgumentParser(description="Todo Manager")

    subparser = parser.add_subparsers(dest="command")

    add_task_parser = subparser.add_parser("add_task")

    mark_done_parser = subparser.add_parser("mark_done")
    mark_done_parser.add_argument("--task_id", type=int, required=True, help="Id of the task to mark done")

    delete_task_parser = subparser.add_parser("delete_task")
    delete_task_parser.add_argument("--task_id", type=int, required=True, help="Id of the task to delete")

    list_task_parser = subparser.add_parser("list_task")
    list_task_parser.add_argument("--only-completed", action="store_true", help="Show only completed tasks")
    list_task_parser.add_argument("--only-due", action="store_true", help="Show only due tasks")
    list_task_parser.add_argument("--last", type=int, help="Show tasks created in the last N days")

    report_parser = subparser.add_parser("task_report")
    report_parser.add_argument("--last", type=int, help="Show report for tasks created in the last N days")

    add_comment_parser = subparser.add_parser("add_comment")
    add_comment_parser.add_argument("--task_id",type = int,required = True,help ="ID of the task to comment on")

    args = parser.parse_args()

    if args.command == "add_task":
        add_task()
    elif args.command == "delete_task":
        delete_task(args.task_id)
    elif args.command == "mark_done":
        mark_done(args.task_id)
    elif args.command == "list_task":
        list_task(only_complete=args.only_completed, only_due=args.only_due, last_n_days=args.last)
    elif args.command == "task_report":
        task_report(last_n_days=args.last)
    elif args.command =="add_comment":
        add_comment(args.task_id)

    else:
        print("No command provided.")    
        




if __name__ == '__main__':
    main()

