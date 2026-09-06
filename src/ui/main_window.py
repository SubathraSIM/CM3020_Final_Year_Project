from src.ui.account_widgets import AvatarButton, PasswordEdit
from src.ui.settings_page import DeleteAccountDialog, LogoutDialog
from src.database.database import create_database, get_user_profile, update_user_profile, delete_user
from PySide6.QtWidgets import QMessageBox
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog,
    QMainWindow,
    QStackedWidget,
)

from src.ui.assistant_page import AssistantPage
from src.database.database import (
    authenticate_user,
    create_user,
    save_consent,
)

from src.ui.assistant_page import AssistantPage
from src.ui.check_in_page import CheckInPage
from src.ui.consent_dialog import (
    ConsentDialog,
    ThankYouDialog,
)
from src.ui.home_page import HomePage
from src.ui.login_page import LoginPage
from src.ui.register_page import RegisterPage
from src.ui.settings_page import SettingsPage
from src.ui.trends_page import TrendsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "Solace Healthcare Wellbeing System"
        )

        self.setMinimumSize(
            1080,
            720,
        )

        theme = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
        image_directory = (Path(__file__).resolve().parents[1] / "images").as_posix()
        self.setStyleSheet(theme.replace("__SOLACE_IMAGES__", image_directory))
        self.showMaximized()

        create_database()
        self.current_user = None
        self.pending_username = ""
        self.current_language = "English"

        self.pages = QStackedWidget()

        self.login_page = LoginPage()
        self.register_page = RegisterPage()
        self.home_page = HomePage()
        self.check_in_page = CheckInPage()
        self.trends_page = TrendsPage()
        self.assistant_page = AssistantPage()
        self.settings_page = SettingsPage()

        for page in (
            self.login_page,
            self.register_page,
            self.home_page,
            self.check_in_page,
            self.trends_page,
            self.assistant_page,
            self.settings_page,
        ):
            self.pages.addWidget(
                page
            )

        self.setCentralWidget(
            self.pages
        )

        self.connect_pages()
        self.settings_page.privacy_requested.connect(self.view_privacy)
        self.settings_page.delete_account_requested.connect(self.confirm_delete_account)
        self.settings_page.profile_panel.save_requested.connect(self.save_profile)
        for avatar in self.findChildren(AvatarButton):
            avatar.clicked.connect(self.show_profile)

    # --------------------------------------------------
    # Page connections
    # --------------------------------------------------

    def connect_pages(self):
        # Login
        self.login_page.login_button.clicked.connect(
            self.login_user
        )

        self.login_page.register_button.clicked.connect(
            self.show_register_page
        )

        self.login_page.language_changed.connect(
            self.change_language
        )

        # Register
        self.register_page.create_button.clicked.connect(
            self.register_user
        )

        self.register_page.back_button.clicked.connect(
            self.show_login_page
        )

        # Home
        self.home_page.check_in_requested.connect(
            self.show_check_in_page
        )

        self.home_page.trends_requested.connect(
            self.show_trends_page
        )

        self.home_page.assistant_requested.connect(
            self.show_assistant_page
        )

        self.home_page.settings_requested.connect(
            self.show_settings_page
        )

        self.home_page.logout_requested.connect(
            self.logout_user
        )

        # Check-in
        self.check_in_page.home_requested.connect(
            self.show_home_page
        )

        self.check_in_page.logout_requested.connect(
            self.logout_user
        )

        self.check_in_page.sidebar.trends_requested.connect(
            self.show_trends_page
        )

        self.check_in_page.sidebar.assistant_requested.connect(
            self.show_assistant_page
        )

        self.check_in_page.sidebar.settings_requested.connect(
            self.show_settings_page
        )

        # Trends
        self.trends_page.home_requested.connect(
            self.show_home_page
        )

        self.trends_page.check_in_requested.connect(
            self.show_check_in_page
        )

        self.trends_page.logout_requested.connect(
            self.logout_user
        )

        self.trends_page.sidebar.assistant_requested.connect(
            self.show_assistant_page
        )

        self.trends_page.sidebar.settings_requested.connect(
            self.show_settings_page
        )

        # Assistant
        self.assistant_page.home_requested.connect(
            self.show_home_page
        )

        self.assistant_page.check_in_requested.connect(
            self.show_check_in_page
        )

        self.assistant_page.trends_requested.connect(
            self.show_trends_page
        )

        self.assistant_page.settings_requested.connect(
            self.show_settings_page
        )

        self.assistant_page.logout_requested.connect(
            self.logout_user
        )

        self.assistant_page.sidebar.assistant_requested.connect(
            self.show_assistant_page
        )

        # Settings
        self.settings_page.home_requested.connect(
            self.show_home_page
        )

        self.settings_page.check_in_requested.connect(
            self.show_check_in_page
        )

        self.settings_page.trends_requested.connect(
            self.show_trends_page
        )

        self.settings_page.sidebar.assistant_requested.connect(
            self.show_assistant_page
        )

        self.settings_page.logout_requested.connect(
            self.logout_user
        )

        self.settings_page.language_changed.connect(
            self.change_language
        )

    # --------------------------------------------------
    # Navigation
    # --------------------------------------------------

    def show_login_page(self):
        self.register_page.clear_status()
        self.login_page.clear_status()

        self.login_page.set_language(
            self.current_language
        )

        self.pages.setCurrentWidget(
            self.login_page
        )

    def show_register_page(self):
        self.login_page.clear_status()
        self.register_page.clear_status()

        self.register_page.set_language(
            self.current_language
        )

        self.pages.setCurrentWidget(
            self.register_page
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

        if self.check_in_page.reset_page():
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

    def show_assistant_page(self):
        if self.current_user is None:
            return

        self.assistant_page.set_user(
            self.current_user["full_name"],
            self.current_user["id"],
        )

        self.assistant_page.set_language(
            self.current_language
        )

        self.assistant_page.refresh_page()

        self.pages.setCurrentWidget(
            self.assistant_page
        )

    def show_settings_page(self):
        if self.current_user is None:
            return
        try:
            profile=get_user_profile(self.current_user["id"])
            panel=self.settings_page.profile_panel
            if profile:
                if panel.loaded_user_id!=profile["id"] or not panel.is_dirty:
                    panel.set_profile(profile)
                self.settings_page.profile_panel.save_button.setEnabled(True)
        except Exception:
            self.settings_page.profile_panel.status.setText(self.settings_page.t("profile_load_failed"))
            self.settings_page.profile_panel.save_button.setEnabled(False)
        self.settings_page.set_language(
            self.current_language
        )

        self.pages.setCurrentWidget(
            self.settings_page
        )

    # --------------------------------------------------
    # Language
    # --------------------------------------------------

    def change_language(
        self,
        language,
    ):
        self.current_language = (
            language
        )

        self.login_page.set_language(
            language
        )

        self.register_page.set_language(
            language
        )

        self.home_page.set_language(
            language
        )

        self.check_in_page.set_language(
            language
        )

        self.trends_page.set_language(
            language
        )

        self.assistant_page.set_language(
            language
        )

        self.settings_page.set_language(
            language
        )

    # --------------------------------------------------
    # Registration
    # --------------------------------------------------

    def register_user(self):
        page = self.register_page

        page.clear_status()

        full_name = (
            page.name_input
            .text()
            .strip()
        )

        username = (
            page.username_input
            .text()
            .strip()
        )

        password = (
            page.password_input
            .text()
        )

        confirm = (
            page.confirm_password_input
            .text()
        )

        if (
            not username
            or not password
            or not confirm
        ):
            page.show_status(
                page.t(
                    "register_empty"
                ),
                "error",
            )

            return

        if not page.valid_password(
            password
        ):
            page.show_status(
                page.t(
                    "password_weak"
                ),
                "error",
            )

            return

        if password != confirm:
            page.show_status(
                page.t(
                    "password_mismatch"
                ),
                "error",
            )

            return

        if not create_user(
            full_name or username,
            username,
            password,
        ):
            page.show_status(
                page.t(
                    "username_exists"
                ),
                "error",
            )

            return

        self.pending_username = (
            username
        )

        page.show_status(
            page.t(
                "account_created"
            ),
            "success",
        )

        self.finish_registration()

    def finish_registration(self):
        self.register_page.clear_fields()

        self.show_login_page()

        self.login_page.username_input.setText(
            self.pending_username
        )

        self.login_page.password_input.setFocus()

        self.login_page.show_status(
            self.login_page.t(
                "account_created_login"
            ),
            "success",
        )

        self.pending_username = ""

    # --------------------------------------------------
    # Login
    # --------------------------------------------------

    def login_user(self):
        page = self.login_page

        page.clear_status()

        username = (
            page.username_input
            .text()
            .strip()
        )

        password = (
            page.password_input
            .text()
        )

        if (
            not username
            or not password
        ):
            page.show_status(
                page.t(
                    "login_empty"
                ),
                "error",
            )

            return

        user = authenticate_user(
            username,
            password,
        )

        if user is None:
            page.show_status(
                page.t(
                    "login_incorrect"
                ),
                "error",
            )

            page.clear_password()

            return

        self.current_user = user
        self.refresh_avatars()

        page.clear_password()

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

        self.assistant_page.set_user(
            user["full_name"],
            user["id"],
        )

        if not user[
            "consent_accepted"
        ]:
            if not self.show_consent_dialog():
                return

        self.pages.setCurrentWidget(
            self.home_page
        )

    # --------------------------------------------------
    # Consent
    # --------------------------------------------------

    def show_consent_dialog(self):
        dialog = ConsentDialog(
            self,
            self.current_language,
        )

        result = dialog.exec()

        self.change_language(
            dialog.selected_language
        )

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

            return True

        ThankYouDialog(
            self.current_language,
            self,
        ).exec()

        self.logout_user()

        return False

    # --------------------------------------------------
    # Logout
    # --------------------------------------------------

    def logout_user(self):
        if self.account_busy():
            QMessageBox.information(self, "Solace", self.settings_page.t("account_busy"))
            return
        if LogoutDialog(self.current_language, self).exec() != QDialog.Accepted:
            return
        if not self.check_in_page.reset_page():
            return
        self.settings_page.profile_panel.set_profile({})
        self.current_user = None
        self.refresh_avatars()

        self.login_page.username_input.clear()
        self.login_page.clear_password()
        self.login_page.clear_status()

        self.check_in_page.reset_page()

        self.trends_page.set_user(
            "",
            None,
        )

        self.assistant_page.set_user(
            "",
            None,
        )

        if not self.assistant_page.worker_running():
            self.assistant_page.clear_chat()

        self.pages.setCurrentWidget(
            self.login_page
        )

        self.login_page.set_language(
            self.current_language
        )

        self.login_page.username_input.setFocus()

    def refresh_avatars(self):
        username = self.current_user['username'] if self.current_user else ''
        for avatar in self.findChildren(AvatarButton):
            avatar.set_identity(username)

    def show_profile(self):
        self.show_settings_page()
        self.settings_page.account_tabs.setCurrentIndex(0)

    def view_privacy(self):
        ConsentDialog(self, self.current_language, view_only=True).exec()

    def account_busy(self):
        p=self.check_in_page
        return (p.video_recording or p.audio_recording
                or (p.analysis_worker is not None and p.analysis_worker.isRunning())
                or (p.transcription_worker is not None and p.transcription_worker.isRunning())
                or self.assistant_page.worker_running())

    def save_profile(self, values):
        panel=self.settings_page.profile_panel
        if self.current_user is None:
            return
        if self.account_busy():
            panel.status.setText(self.settings_page.t('account_busy'))
            return
        panel.save_button.setEnabled(False)
        try:
            user=update_user_profile(self.current_user['id'], **values)
            self.current_user.update(user)
            panel.set_profile(user)
            self.home_page.set_user(user['full_name'])
            self.refresh_avatars()
            panel.status.setText(self.settings_page.t('profile_saved'))
        except ValueError as error:
            panel.status.setText(self.settings_page.t(str(error)))
        except Exception:
            panel.status.setText(self.settings_page.t('profile_failed'))
        finally:
            panel.clear_sensitive()
            panel.save_button.setEnabled(True)

    def confirm_delete_account(self):
        if self.current_user is None:
            return
        if self.account_busy():
            QMessageBox.information(self, 'Solace', self.settings_page.t('account_busy'))
            return
        dialog=DeleteAccountDialog(self.current_language,self)
        if dialog.exec()!=QDialog.Accepted:
            return
        try:
            deleted=delete_user(self.current_user['id'])
        except Exception:
            deleted=False
        if not deleted:
            QMessageBox.warning(self,'Solace',self.settings_page.t('delete_failed'))
            return
        self.check_in_page.reset_page()
        self.logout_user()

    def closeEvent(self, event):
        if self.account_busy():
            QMessageBox.information(self, 'Solace', self.settings_page.t('account_busy'))
            event.ignore()
            return
        self.check_in_page.reset_page()
        self.settings_page.profile_panel.clear_sensitive()
        super().closeEvent(event)
