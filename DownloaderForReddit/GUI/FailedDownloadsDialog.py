"""
Downloader for Reddit takes a list of reddit users and subreddits and downloads content posted to reddit either by the
users or on the subreddits.


Copyright (C) 2017, Kyle Hickey


This file is part of the Downloader for Reddit.

Downloader for Reddit is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Downloader for Reddit is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Downloader for Reddit.  If not, see <http://www.gnu.org/licenses/>.
"""


from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QCursor

from GUI_Resources.FailedDownloadsDialog_auto import Ui_failed_downloads_dialog
from ViewModels.FailedDownloadsDialogModels import FailedDownloadsTableModel, FailedDownloadsDetailTableModel
from Utils import Injector
from Utils import SystemUtil


class FailedDownloadsDialog(QtWidgets.QDialog, Ui_failed_downloads_dialog):

    def __init__(self, fail_list):
        """
        A dialog box that shows the failed downloads and any relevant information about them, such as: the user that
        posted the content to reddit, the subreddit it was posted in, the title of the post, the url that failed and
        a reason as to why it failed (ex: download or extraction error)

        :param fail_list: A list supplied to the dialog of the failed content
        """
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)
        self.settings_manager = Injector.get_settings_manager()
        geom = self.settings_manager.failed_downloads_dialog_geom
        self.restoreGeometry(geom if geom is not None else self.saveGeometry())
        splitter_state = self.settings_manager.failed_downloads_dialog_splitter_state
        self.splitter.restoreState(splitter_state if splitter_state is not None else self.splitter.saveState())

        self.setWindowTitle('%s failed downloads' % len(fail_list))

        self.detail_model = None
        self.detail_table.setColumnWidth(0, 40)
        self.detail_table.horizontalHeader().setStretchLastSection(True)
        self.detail_table.setVisible(False)

        self.table_model = FailedDownloadsTableModel(fail_list)
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.table_view.setColumnWidth(3, 215)
        self.table_view.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)
        self.table_view.clicked.connect(self.setup_detail_table)

        self.table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.display_context_menu)

        self.buttonBox.accepted.connect(self.accept)

    def display_context_menu(self):
        menu = QtWidgets.QMenu()
        index = self.table_view.selectedIndexes()[0].row()
        post = self.table_model.data_list[index]
        visit_author_reddit = menu.addAction('Visit Author Page')
        visit_subreddit = menu.addAction('Visit Subreddit')
        visit_post_page = menu.addAction('Visit Post')
        menu.addSeparator()
        export_url_list = menu.addAction('Export Url List')
        menu.addSeparator()
        export_as_text = menu.addAction('Export Posts As Text')
        export_as_json = menu.addAction('Export Posts As Json')
        export_as_xml = menu.addAction('Export Posts As Xml')

        visit_author_reddit.triggered.connect(lambda: SystemUtil.open_in_system('www.reddit.com/u/%s' % post.author))
        visit_subreddit.triggered.connect(lambda: SystemUtil.open_in_system('www.reddit.com/r/%s' % post.subreddit))
        visit_post_page.triggered.connect(lambda: SystemUtil.open_in_system(post.url))

        menu.exec_(QCursor.pos())

    def setup_detail_table(self):
        """Sets up the detail table to display the selected post."""
        post = self.table_model.data_list[self.table_view.currentIndex().row()]
        self.detail_model = FailedDownloadsDetailTableModel(post)
        self.detail_table.setModel(self.detail_model)
        self.detail_table.setVisible(True)

    def close_detail_table(self):
        self.detail_table.setVisible(False)

    def accept(self):
        self.save_settings()
        super().accept()

    def closeEvent(self, event):
        self.save_settings()

    def save_settings(self):
        self.settings_manager.failed_downloads_dialog_geom = self.saveGeometry()
        self.settings_manager.failed_downloads_dialog_splitter_state = self.splitter.saveState()
        self.settings_manager.save_failed_downloads_dialog()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            if self.detail_table.isVisible():
                self.close_detail_table()
            else:
                self.close()
