from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QDialog,
    QMainWindow,
    QStackedWidget,
)

from src.database.database import (
    authenticate_user,
    create_user,
    save_consent,
)
from src.ui.check_in_page import CheckInPage
from src.ui.consent_dialog import (
    ConsentDialog,
    ThankYouDialog,
)
from src.ui.home_page import HomePage
from src.ui.login_page import LoginPage
from src.ui.register_page import RegisterPage
from src.ui.trends_page import TrendsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "Solace Healthcare Wellbeing System"
        )
        self.setMinimumSize(1080, 720)

        self.current_user = None
        self.pending_username = ""

        self.pages = QStackedWidget()

        self.login_page = LoginPage()
        self.register_page = RegisterPage()
        self.home_page = HomePage()
        self.check_in_page = CheckInPage()
        self.trends_page = TrendsPage()

        self.pages.addWidget(
            self.login_page
        )
        self.pages.addWidget(
            self.register_page
        )
        self.pages.addWidget(
            self.home_page
        )
        self.pages.addWidget(
            self.check_in_page
        )
        self.pages.addWidget(
            self.trends_page
        )

        self.setCentralWidget(self.pages)

        self.login_page.login_button.clicked.connect(
            self.login_user
        )
        self.login_page.register_button.clicked.connect(
            self.show_register_page
        )

        self.register_page.create_button.clicked.connect(
            self.register_user
        )
        self.register_page.back_button.clicked.connect(
            self.show_login_page
        )

        self.home_page.check_in_requested.connect(
            self.show_check_in_page
        )
        self.home_page.trends_requested.connect(
            self.show_trends_page
        )
        self.home_page.logout_requested.connect(
            self.logout_user
        )

        self.check_in_page.home_requested.connect(
            self.show_home_page
        )
        self.check_in_page.logout_requested.connect(
            self.logout_user
        )
        self.check_in_page.sidebar.trends_requested.connect(
            self.show_trends_page
        )

        self.trends_page.home_requested.connect(
            self.show_home_page
        )
        self.trends_page.check_in_requested.connect(
            self.show_check_in_page
        )
        self.trends_page.logout_requested.connect(
            self.logout_user
        )

    def show_register_page(self):
        self.login_page.clear_status()
        self.register_page.clear_status()

        self.pages.setCurrentWidget(
            self.register_page
        )

    def show_login_page(self):
        self.register_page.clear_status()
        self.login_page.clear_status()

        self.pages.setCurrentWidget(
            self.login_page
        )

    def show_home_page(self):
        self.pages.setCurrentWidget(
            self.home_page
        )

    def show_check_in_page(self):
        if self.current_user is None:
            return

        self.check_in_page.set_user(
            self.current_user["full_name"],
            self.current_user["id"],
        )
        self.check_in_page.reset_page()

        self.pages.setCurrentWidget(
            self.check_in_page
        )

    def show_trends_page(self):
        if self.current_user is None:
            return

        self.trends_page.set_user(
            self.current_user["full_name"],
            self.current_user["id"],
        )
        self.trends_page.refresh_page()

        self.pages.setCurrentWidget(
            self.trends_page
        )

    def register_user(self):
        self.register_page.clear_status()

        full_name = (
            self.register_page
            .name_input
            .text()
            .strip()
        )
        username = (
            self.register_page
            .username_input
            .text()
            .strip()
        )
        password = (
            self.register_page
            .password_input
            .text()
        )
        confirm_password = (
            self.register_page
            .confirm_password_input
            .text()
        )

        if not all(
            [
                full_name,
                username,
                password,
                confirm_password,
            ]
        ):
            self.register_page.show_status(
                "Please complete all fields.",
                "error",
            )
            return

        if password != confirm_password:
            self.register_page.show_status(
                "The passwords do not match.",
                "error",
            )
            return

        created = create_user(
            full_name,
            username,
            password,
        )

        if not created:
            self.register_page.show_status(
                "This username is already "
                "registered.",
                "error",
            )
            return

        self.pending_username = username

        self.register_page.show_status(
            "Account created successfully.",
            "success",
        )

        QTimer.singleShot(
            1300,
            self.finish_registration,
        )

    def finish_registration(self):
        self.register_page.clear_fields()
        self.show_login_page()

        self.login_page.username_input.setText(
            self.pending_username
        )
        self.login_page.password_input.setFocus()

        self.login_page.show_status(
            "Account created. You can log in now.",
            "success",
        )

        self.pending_username = ""

    def login_user(self):
        self.login_page.clear_status()

        username = (
            self.login_page
            .username_input
            .text()
            .strip()
        )
        password = (
            self.login_page
            .password_input
            .text()
        )

        if not username or not password:
            self.login_page.show_status(
                "Please enter your username "
                "and password.",
                "error",
            )
            return

        user = authenticate_user(
            username,
            password,
        )

        if user is None:
            self.login_page.show_status(
                "The username or password "
                "is incorrect.",
                "error",
            )
            self.login_page.clear_password()
            self.login_page.password_input.setFocus()
            return

        self.current_user = user
        self.login_page.clear_password()

        self.home_page.set_user(
            user["full_name"]
        )
        self.check_in_page.set_user(
            user["full_name"],
            user["id"],
        )
        self.trends_page.set_user(
            user["full_name"],
            user["id"],
        )

        self.pages.setCurrentWidget(
            self.home_page
        )

        if not user["consent_accepted"]:
            QTimer.singleShot(
                180,
                self.show_consent_dialog,
            )

    def show_consent_dialog(self):
        if self.current_user is None:
            return

        consent_dialog = ConsentDialog(self)
        result = consent_dialog.exec()

        if (
            result
            == QDialog.DialogCode.Accepted
        ):
            save_consent(
                self.current_user["id"]
            )
            self.current_user[
                "consent_accepted"
            ] = True
            return

        thank_you_dialog = (
            ThankYouDialog(self)
        )
        thank_you_dialog.exec()
        self.logout_user()

    def logout_user(self):
        self.current_user = None

        self.login_page.username_input.clear()
        self.login_page.password_input.clear()
        self.login_page.clear_status()

        self.check_in_page.reset_page()
        self.trends_page.set_user("", None)

        self.pages.setCurrentWidget(
            self.login_page
        )
        self.login_page.username_input.setFocus()
