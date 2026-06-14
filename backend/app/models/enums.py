from enum import Enum


class TaskStatus(str, Enum):
    CREATED = "created"
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    AI_PARTIAL_FAILED = "ai_partial_failed"


class RelationType(str, Enum):
    MAIN = "main"
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"


class DataType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    DATE = "date"
    DATETIME = "datetime"
    PERCENT = "percent"
    BOOLEAN = "boolean"
    AMOUNT = "amount"


class ValidationLevel(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"


class TableRole(str, Enum):
    MAIN = "main"
    AUX = "aux"


class AIBlockStatus(str, Enum):
    NOT_USED = "not_used"
    SUCCESS = "success"
    FAILED = "failed"


class AIStatus(str, Enum):
    NOT_USED = "not_used"
    SUCCESS = "success"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
