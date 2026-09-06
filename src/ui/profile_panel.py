from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QLineEdit,QPushButton,QFrame
from src.ui.account_widgets import AvatarButton, PasswordEdit
from src.ui.translations import ENGLISH_TEXT,get_text

ENGLISH_TEXT.update({
 'profile_username_required':'Enter a username.',
 'profile_account_missing':'This account no longer exists. Please sign in again.',
 'profile_password_incorrect':'Enter your correct current password to change your username or password.',
 'profile_saved':'Your profile has been saved.',
 'profile_failed':'Your profile could not be saved. Please try again.',
 'profile_optional':'Optional details',
 'profile_details_note':'Only your username and password are required. Add other details if you wish.',
 'profile_full_name':'Full name (optional)', 'profile_email':'Email (optional)',
 'profile_profession':'Profession (optional)', 'profile_address':'Address (optional)',
 'profile_current_password':'Current password', 'profile_new_password':'New password (optional)',
 'profile_confirm_password':'Confirm new password',
 'profile_password_note':'Leave these fields blank to keep your password. Your current password is required when changing your username or password.',
 'profile_save':'Save profile', 'profile_tab':'Profile', 'preferences_tab':'Preferences',
 'profile_load_failed':'Your profile could not be loaded. Reopen settings to try again.',
 'delete_failed':'Your account could not be deleted. Please try again.',
 'account_busy':'Wait for the current recording or analysis to finish before changing your account.',
 'register_name_optional':'Full name (optional)',
})

class ProfilePanel(QWidget):
    save_requested=Signal(dict)
    def __init__(self):
        super().__init__()
        self.setObjectName('profilePanel')
        self.setAttribute(Qt.WA_StyledBackground,True)
        self.is_dirty=False
        self._loading=False
        self.loaded_user_id=None
        self.current_language='English'
        self.labels=[]
        self.fields={}
        layout=QVBoxLayout(self);layout.setContentsMargins(20,16,20,16);layout.setSpacing(12)
        row=QHBoxLayout();self.avatar=AvatarButton();self.name=QLabel();self.name.setObjectName('sectionTitle')
        row.addWidget(self.avatar);row.addWidget(self.name);row.addStretch();layout.addLayout(row)
        self.note=QLabel();self.note.setWordWrap(True);self.note.setObjectName('featureDescription');layout.addWidget(self.note)
        grid=QGridLayout();grid.setHorizontalSpacing(24);grid.setVerticalSpacing(8)
        for i,(key,text) in enumerate([('username','username'),('full_name','profile_full_name'),('email','profile_email'),('profession','profile_profession'),('address','profile_address')]):
            label=QLabel();field=QLineEdit();field.setMinimumHeight(38);label.setBuddy(field)
            self.labels.append((label,text));self.fields[key]=field
            row,col=divmod(i,2);grid.addWidget(label,row*2,col);grid.addWidget(field,row*2+1,col)
        layout.addLayout(grid)
        self.password_note=QLabel();self.password_note.setWordWrap(True);self.password_note.setObjectName('privacyNote');layout.addWidget(self.password_note)
        passwords=QGridLayout();passwords.setHorizontalSpacing(16)
        for col,(key,text) in enumerate([('current_password','profile_current_password'),('new_password','profile_new_password'),('confirm_password','profile_confirm_password')]):
            label=QLabel();field=PasswordEdit();field.setMinimumHeight(40);label.setBuddy(field)
            self.labels.append((label,text));self.fields[key]=field;passwords.addWidget(label,0,col);passwords.addWidget(field,1,col)
        layout.addLayout(passwords)
        self.status=QLabel();self.status.setWordWrap(True);self.status.setObjectName('profileStatus');layout.addWidget(self.status)
        self.save_button=QPushButton();self.save_button.setObjectName('primaryButton');self.save_button.setMinimumHeight(44)
        self.save_button.clicked.connect(self.submit);layout.addWidget(self.save_button);layout.addStretch()
        for field in self.fields.values():
            field.textChanged.connect(self.mark_dirty)
        self.set_language('English')

    def set_language(self,language):
        self.current_language=language
        t=lambda key:get_text(language,key)
        for label,key in self.labels:label.setText(t(key))
        self.note.setText(t('profile_details_note'));self.password_note.setText(t('profile_password_note'))
        self.save_button.setText(t('profile_save'))
        for field in self.fields.values():
            if isinstance(field,PasswordEdit):field.refresh_eye()

    def set_profile(self,profile):
        self._loading=True
        self.loaded_user_id=profile.get("id")
        self.clear_sensitive()
        for key in ('username','full_name','email','profession','address'):
            self.fields[key].setText(str(profile.get(key) or ''))
        self.name.setText(profile.get('username',''))
        self.avatar.set_identity(profile.get('username',''))
        self.status.clear()
        self._loading=False
        self.is_dirty=False

    def clear_sensitive(self):
        for key in ('current_password','new_password','confirm_password'):self.fields[key].clear()

    def submit(self):
        values={key:field.text() for key,field in self.fields.items()}
        if values['new_password']!=values.pop('confirm_password'):
            self.status.setText(get_text(self.current_language,'password_mismatch'));return
        self.save_requested.emit(values)

    def mark_dirty(self):
        if not self._loading:
            self.is_dirty=True
