from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date
from datetime import datetime, timedelta
from calendar import day_name
from sqlalchemy.orm import sessionmaker
from enum import Enum, auto

Base = declarative_base()


class Task(Base):
    __tablename__ = 'task'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task = Column(String)
    deadline = Column(Date, default=datetime.today())

    def __repr__(self):
        return str(self.id) + ". " + self.task


class DatabaseWrapper:
    def __init__(self, database_name):
        self._engine = create_engine(f'sqlite:///{database_name}?check_same_thread=False')
        Base.metadata.create_all(self._engine)
        Session = sessionmaker(bind=self._engine)
        self._session = Session()

    def get_engine(self):
        return self._engine

    def get_session(self):
        return self._session

    def get_rows(self, table_name=Task, filter=True):
        return self._session.query(table_name).filter(filter).all()

    def get_sorted_rows(self, table_name=Task, filter=True, order_by=Task.deadline):
        return self._session.query(table_name).filter(filter).order_by(order_by)

    def delete_row(self, filter, table_name=Task):
        self._session.query(table_name).filter(filter).delete()
        self._session.commit()


class TaskManagerFacade:

    def __init__(self, database_wrapper):
        self._wrapper = database_wrapper

    def _show_task(self, day, filter):
        rows = self._wrapper.get_rows(filter=filter)
        print(f'{day_name[day.weekday()]} {day.day} {day.strftime("%b")}:')
        for row in rows:
            print(row)

        if not rows:
            print('Nothing to do!')
        print()

    @staticmethod
    def _print_tasks(rows, msg):
        if not rows:
            print(msg)
            return
        for row in rows:
            date = row.deadline
            print(f'{row} {date.day} {date.strftime("%b")}')

    def show_today_tasks(self):
        today = datetime.today().date()
        self._show_task(today, Task.deadline == today)

    def show_week_tasks(self):
        today = datetime.today().date()
        next_week_day = today + timedelta(days=7)
        while today < next_week_day:
            self._show_task(today, Task.deadline == today)
            print()
            today += timedelta(days=1)

    def show_all_tasks(self):
        rows = self._wrapper.get_rows()
        self._print_tasks(rows, 'Nothing to do!')
        print()

    def show_missed_task(self):
        print('Missed tasks:')
        today = datetime.today().date()
        rows = self._wrapper.get_sorted_rows(filter=Task.deadline < today)
        self._print_tasks(rows, 'Nothing is missing!')
        print()

    def add_task(self, task_name, deadline):
        session = self._wrapper.get_session()
        new_row = Task(task=task_name,
                       deadline=datetime.strptime(deadline, '%Y-%m-%d').date())
        session.add(new_row)
        session.commit()
        print()
        print('Task has been added!')
        print()

    def delete_task(self):
        print('Chose the number of the task you want to delete:')
        rows = self._wrapper.get_sorted_rows()
        self._print_tasks(rows, 'Nothing to delete!')
        idx = int(input(''))
        self._wrapper.delete_row(Task.id == idx)
        print('Task has been deleted')
        print()


def menu():
    print("1) Today's tasks")
    print("2) Week's tasks")
    print("3) All tasks")
    print("4) Missed tasks")
    print("5) Add Task")
    print("6) Delete Task")
    print("0) Exit")


class ICommandHandler:
    class UserCommand(Enum):
        SHOW_TODAY_TASKS = auto()
        SHOW_WEEK_TASKS = auto()
        SHOW_ALL_TASKS = auto()
        SHOW_MISSED_TASKS = auto()
        ADD_TASK = auto()
        DELETE_TASK = auto()

        def __eq__(self, other):
            return self.value == other

    def __init__(self, task_manager, next_handler):
        self._task_manager = task_manager
        self._next_handler = next_handler

    def _process_next_handler(self, request):
        if self._next_handler is not None:
            self._next_handler.handle(request)


class ShowTodayTasksHandler(ICommandHandler):

    def __init__(self, task_manager):
        super().__init__(task_manager, ShowWeekTasks(task_manager))

    def handle(self, request):
        if request == self.UserCommand.SHOW_TODAY_TASKS:
            self._task_manager.show_today_tasks()

        self._process_next_handler(request)


class ShowWeekTasks(ICommandHandler):
    def __init__(self, task_manager):
        super().__init__(task_manager, ShowAllTasks(task_manager))

    def handle(self, request):
        if request == self.UserCommand.SHOW_WEEK_TASKS:
            self._task_manager.show_week_tasks()

        self._process_next_handler(request)


class ShowAllTasks(ICommandHandler):
    def __init__(self, task_manager):
        super().__init__(task_manager, ShowMissedTasks(task_manager))

    def handle(self, request):
        if request == self.UserCommand.SHOW_ALL_TASKS:
            self._task_manager.show_all_tasks()

        self._process_next_handler(request)


class ShowMissedTasks(ICommandHandler):
    def __init__(self, task_manager):
        super().__init__(task_manager, AddTaskHandler(task_manager))

    def handle(self, request):
        if request == self.UserCommand.SHOW_MISSED_TASKS:
            self._task_manager.show_missed_task()

        self._process_next_handler(request)


class AddTaskHandler(ICommandHandler):
    def __init__(self, task_manager):
        super().__init__(task_manager, DeleteTaskHandler(task_manager))

    def handle(self, request):
        if request == self.UserCommand.ADD_TASK:
            print()
            task_name = input('Enter task')
            deadline = input('Enter deadline')
            self._task_manager.add_task(task_name, deadline)

        self._process_next_handler(request)


class DeleteTaskHandler(ICommandHandler):
    def __init__(self, task_manager):
        super().__init__(task_manager, None)

    def handle(self, request):
        if request == self.UserCommand.DELETE_TASK:
            print()
            self._task_manager.delete_task()

        self._process_next_handler(request)


if __name__ == '__main__':
    task_manager = TaskManagerFacade(DatabaseWrapper('todo.db'))
    commandHandler = ShowTodayTasksHandler(task_manager)
    while True:
        menu()
        try:
            request = int(input())
            if request == 0:
                print('Bye!')
                break
            commandHandler.handle(request)
        except ValueError:
            print('User command should be integer type value from 0 to 6')
            print()
