from .vo import TaskStatus

# Возможные переходы между статусами задачи
ALLOWED_TRANSITIONS: dict[TaskStatus: list[TaskStatus]] = {
    TaskStatus.BACKLOG: [TaskStatus.TODO, TaskStatus.CANCELLED],
    TaskStatus.TODO: [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.CANCELLED],
    TaskStatus.IN_PROGRESS: [
        TaskStatus.BLOCKED, TaskStatus.REVIEW, TaskStatus.DONE, TaskStatus.CANCELLED
    ],
    TaskStatus.BLOCKED: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
    TaskStatus.REVIEW: [TaskStatus.IN_PROGRESS, TaskStatus.DONE, TaskStatus.CANCELLED],
    TaskStatus.DONE: [],
    TaskStatus.CANCELLED: [],
}

# Разрешённые статусы для редактирования задачи
ALLOWED_EDIT_STATUSES: set[TaskStatus] = {
    TaskStatus.BACKLOG, TaskStatus.TODO,
}

# Разрешённые статусы для назначения задачи
ALLOWED_ASSIGN_STATUSES: set[TaskStatus] = {
    TaskStatus.BACKLOG,
    TaskStatus.TODO,
    TaskStatus.IN_PROGRESS,
    TaskStatus.BLOCKED,
    TaskStatus.REVIEW,
}

# Маппинг статусов задач в русские представления для UI
TASK_STATUS_LABEL_MAP: dict[TaskStatus, str] = {
    TaskStatus.BACKLOG: "В резерве",
    TaskStatus.TODO: "Готово к выполнению",
    TaskStatus.IN_PROGRESS: "В работе",
    TaskStatus.REVIEW: "На проверке",
    TaskStatus.BLOCKED: "Приостановлено",
    TaskStatus.DONE: "Выполнено",
    TaskStatus.CANCELLED: "Отменено",
}
