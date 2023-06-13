from app.modules.db_controller import DbController


class DialogBot():
    db: DbController = None

    def __init__(self) -> None:
        db = DbController()

    def run(self):
        pass
