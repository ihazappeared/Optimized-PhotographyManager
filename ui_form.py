# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QProgressBar, QPushButton, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.resize(800, 530)
        icon = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.CameraPhoto))
        Widget.setWindowIcon(icon)
        Widget.setWindowOpacity(1.000000000000000)
        self.verticalLayout_4 = QVBoxLayout(Widget)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.DirectoryBox = QGroupBox(Widget)
        self.DirectoryBox.setObjectName(u"DirectoryBox")
        self.DirectoryBox.setEnabled(True)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.DirectoryBox.sizePolicy().hasHeightForWidth())
        self.DirectoryBox.setSizePolicy(sizePolicy)
        self.horizontalLayout = QHBoxLayout(self.DirectoryBox)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.base_dir_edit = QLineEdit(self.DirectoryBox)
        self.base_dir_edit.setObjectName(u"base_dir_edit")
        self.base_dir_edit.setMouseTracking(True)
        self.base_dir_edit.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self.horizontalLayout.addWidget(self.base_dir_edit)

        self.browse_button = QPushButton(self.DirectoryBox)
        self.browse_button.setObjectName(u"browse_button")
        self.browse_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.horizontalLayout.addWidget(self.browse_button)


        self.verticalLayout_4.addWidget(self.DirectoryBox)

        self.MainLayout = QHBoxLayout()
        self.MainLayout.setObjectName(u"MainLayout")
        self.ActionsBox = QGroupBox(Widget)
        self.ActionsBox.setObjectName(u"ActionsBox")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(2)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.ActionsBox.sizePolicy().hasHeightForWidth())
        self.ActionsBox.setSizePolicy(sizePolicy1)
        self.ActionsBox.setStyleSheet(u"QProgressBar::chunk {\n"
"    background-color: #888;  \n"
"    border-radius: 5px;\n"
"    margin: 0px;\n"
"}")
        self.verticalLayout_5 = QVBoxLayout(self.ActionsBox)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.OptionsBox = QGroupBox(self.ActionsBox)
        self.OptionsBox.setObjectName(u"OptionsBox")
        self.verticalLayout = QVBoxLayout(self.OptionsBox)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.format_label = QLabel(self.OptionsBox)
        self.format_label.setObjectName(u"format_label")
        self.format_label.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_2.addWidget(self.format_label)

        self.format_comboBox = QComboBox(self.OptionsBox)
        self.format_comboBox.addItem("")
        self.format_comboBox.addItem("")
        self.format_comboBox.addItem("")
        self.format_comboBox.addItem("")
        self.format_comboBox.setObjectName(u"format_comboBox")

        self.horizontalLayout_2.addWidget(self.format_comboBox)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.rem_empty_checkbox = QCheckBox(self.OptionsBox)
        self.rem_empty_checkbox.setObjectName(u"rem_empty_checkbox")

        self.verticalLayout.addWidget(self.rem_empty_checkbox)

        self.sep_videos_checkbox = QCheckBox(self.OptionsBox)
        self.sep_videos_checkbox.setObjectName(u"sep_videos_checkbox")

        self.verticalLayout.addWidget(self.sep_videos_checkbox)


        self.verticalLayout_5.addWidget(self.OptionsBox)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.flatten_button = QPushButton(self.ActionsBox)
        self.flatten_button.setObjectName(u"flatten_button")
        self.flatten_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.horizontalLayout_6.addWidget(self.flatten_button)

        self.clean_filenames_button = QPushButton(self.ActionsBox)
        self.clean_filenames_button.setObjectName(u"clean_filenames_button")
        self.clean_filenames_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.horizontalLayout_6.addWidget(self.clean_filenames_button)


        self.verticalLayout_5.addLayout(self.horizontalLayout_6)

        self.reset_all_button = QPushButton(self.ActionsBox)
        self.reset_all_button.setObjectName(u"reset_all_button")
        self.reset_all_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.verticalLayout_5.addWidget(self.reset_all_button)

        self.start_button = QPushButton(self.ActionsBox)
        self.start_button.setObjectName(u"start_button")
        self.start_button.setMinimumSize(QSize(0, 0))
        self.start_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.start_button.setStyleSheet(u"height:22px;")
        icon1 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart))
        self.start_button.setIcon(icon1)

        self.verticalLayout_5.addWidget(self.start_button)

        self.progress_bar = QProgressBar(self.ActionsBox)
        self.progress_bar.setObjectName(u"progress_bar")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.progress_bar.sizePolicy().hasHeightForWidth())
        self.progress_bar.setSizePolicy(sizePolicy2)
        self.progress_bar.setMinimumSize(QSize(0, 0))
        self.progress_bar.setMaximumSize(QSize(16777215, 30))
        self.progress_bar.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.progress_bar.setAutoFillBackground(False)
        self.progress_bar.setStyleSheet(u"height: 22px;\n"
"border: 1px solid #444;\n"
"border-radius: 6px;\n"
"text-align: center;\n"
"font-weight: bold;\n"
"\n"
"")
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setTextVisible(True)

        self.verticalLayout_5.addWidget(self.progress_bar)


        self.MainLayout.addWidget(self.ActionsBox)

        self.ExcludedFoldersPanel = QGroupBox(Widget)
        self.ExcludedFoldersPanel.setObjectName(u"ExcludedFoldersPanel")
        sizePolicy1.setHeightForWidth(self.ExcludedFoldersPanel.sizePolicy().hasHeightForWidth())
        self.ExcludedFoldersPanel.setSizePolicy(sizePolicy1)
        self.verticalLayout_7 = QVBoxLayout(self.ExcludedFoldersPanel)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.excluded_list = QListWidget(self.ExcludedFoldersPanel)
        self.excluded_list.setObjectName(u"excluded_list")

        self.verticalLayout_7.addWidget(self.excluded_list)

        self.ExcludedButtons = QHBoxLayout()
        self.ExcludedButtons.setObjectName(u"ExcludedButtons")
        self.add_excluded_button = QPushButton(self.ExcludedFoldersPanel)
        self.add_excluded_button.setObjectName(u"add_excluded_button")
        self.add_excluded_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.ExcludedButtons.addWidget(self.add_excluded_button)

        self.remove_excluded_button = QPushButton(self.ExcludedFoldersPanel)
        self.remove_excluded_button.setObjectName(u"remove_excluded_button")
        self.remove_excluded_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.ExcludedButtons.addWidget(self.remove_excluded_button)


        self.verticalLayout_7.addLayout(self.ExcludedButtons)


        self.MainLayout.addWidget(self.ExcludedFoldersPanel)


        self.verticalLayout_4.addLayout(self.MainLayout)

        self.StatsBox = QGroupBox(Widget)
        self.StatsBox.setObjectName(u"StatsBox")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.StatsBox.sizePolicy().hasHeightForWidth())
        self.StatsBox.setSizePolicy(sizePolicy3)
        self.StatsBox.setFlat(False)
        self.horizontalLayout_4 = QHBoxLayout(self.StatsBox)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.total_label = QLabel(self.StatsBox)
        self.total_label.setObjectName(u"total_label")

        self.horizontalLayout_4.addWidget(self.total_label)

        self.total_lineEdit = QLineEdit(self.StatsBox)
        self.total_lineEdit.setObjectName(u"total_lineEdit")
        self.total_lineEdit.setEnabled(False)
        self.total_lineEdit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.total_lineEdit.setReadOnly(True)

        self.horizontalLayout_4.addWidget(self.total_lineEdit)

        self.moved_label = QLabel(self.StatsBox)
        self.moved_label.setObjectName(u"moved_label")

        self.horizontalLayout_4.addWidget(self.moved_label)

        self.moved_lineEdit = QLineEdit(self.StatsBox)
        self.moved_lineEdit.setObjectName(u"moved_lineEdit")
        self.moved_lineEdit.setEnabled(False)
        self.moved_lineEdit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.moved_lineEdit.setReadOnly(True)

        self.horizontalLayout_4.addWidget(self.moved_lineEdit)

        self.skipped_label = QLabel(self.StatsBox)
        self.skipped_label.setObjectName(u"skipped_label")

        self.horizontalLayout_4.addWidget(self.skipped_label)

        self.skipped_lineEdit = QLineEdit(self.StatsBox)
        self.skipped_lineEdit.setObjectName(u"skipped_lineEdit")
        self.skipped_lineEdit.setEnabled(False)
        self.skipped_lineEdit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.skipped_lineEdit.setReadOnly(True)

        self.horizontalLayout_4.addWidget(self.skipped_lineEdit)


        self.verticalLayout_4.addWidget(self.StatsBox)

        self.Log = QWidget(Widget)
        self.Log.setObjectName(u"Log")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(1)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.Log.sizePolicy().hasHeightForWidth())
        self.Log.setSizePolicy(sizePolicy4)
        self.verticalLayout_2 = QVBoxLayout(self.Log)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.log_label = QLabel(self.Log)
        self.log_label.setObjectName(u"log_label")

        self.verticalLayout_2.addWidget(self.log_label)

        self.log_list = QTextEdit(self.Log)
        self.log_list.setObjectName(u"log_list")
        self.log_list.setReadOnly(True)
        self.log_list.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        self.verticalLayout_2.addWidget(self.log_list)


        self.verticalLayout_4.addWidget(self.Log)


        self.retranslateUi(Widget)

        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(QCoreApplication.translate("Widget", u"Photo Organizer", None))
        self.DirectoryBox.setTitle(QCoreApplication.translate("Widget", u"Base Directory", None))
        self.browse_button.setText(QCoreApplication.translate("Widget", u"Browse", None))
        self.ActionsBox.setTitle(QCoreApplication.translate("Widget", u"Actions", None))
        self.OptionsBox.setTitle("")
        self.format_label.setText(QCoreApplication.translate("Widget", u"Folder Structure:", None))
        self.format_comboBox.setItemText(0, QCoreApplication.translate("Widget", u"By Day (YYYY-MM-DD)", None))
        self.format_comboBox.setItemText(1, QCoreApplication.translate("Widget", u"By Year / Month / Day", None))
        self.format_comboBox.setItemText(2, QCoreApplication.translate("Widget", u"By Year / Month", None))
        self.format_comboBox.setItemText(3, QCoreApplication.translate("Widget", u"By Year / Day-Of-Year", None))

        self.rem_empty_checkbox.setText(QCoreApplication.translate("Widget", u"Remove Empty Folders", None))
        self.sep_videos_checkbox.setText(QCoreApplication.translate("Widget", u"Separate Videos", None))
        self.flatten_button.setText(QCoreApplication.translate("Widget", u"Flatten Structure", None))
        self.clean_filenames_button.setText(QCoreApplication.translate("Widget", u"Clean Filenames", None))
        self.reset_all_button.setText(QCoreApplication.translate("Widget", u"Reset All Settings", None))
        self.start_button.setText(QCoreApplication.translate("Widget", u" Start", None))
        self.progress_bar.setFormat(QCoreApplication.translate("Widget", u"%p%", None))
        self.ExcludedFoldersPanel.setTitle(QCoreApplication.translate("Widget", u"Excluded Folders", None))
        self.add_excluded_button.setText(QCoreApplication.translate("Widget", u"Add Folder", None))
        self.remove_excluded_button.setText(QCoreApplication.translate("Widget", u"Remove Folder", None))
        self.StatsBox.setTitle(QCoreApplication.translate("Widget", u"Stats", None))
        self.total_label.setText(QCoreApplication.translate("Widget", u"Total:", None))
        self.moved_label.setText(QCoreApplication.translate("Widget", u"Moved:", None))
        self.skipped_label.setText(QCoreApplication.translate("Widget", u"Skipped:", None))
        self.log_label.setText(QCoreApplication.translate("Widget", u"Log Output", None))
    # retranslateUi

