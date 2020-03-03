import os
from datetime import datetime
from sqlalchemy import Column, Integer, SmallInteger, String, Boolean, DateTime, ForeignKey, Table, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import Session

from .DatabaseHandler import DatabaseHandler
from .ModelEnums import DownloadNameMethod, SubredditSaveStructure, CommentDownload
from ..Core import Const
from ..Utils import SystemUtil


Base = DatabaseHandler.base


class BaseModel(Base):

    __abstract__ = True

    def get_session(self):
        return Session.object_session(self)


list_association = Table(
    'reddit_object_list_assoc', Base.metadata,
    Column('list_id', Integer, ForeignKey('reddit_object_lists.id')),
    Column('reddit_object_id', Integer, ForeignKey('reddit_object.id'))
)


class RedditObjectList(BaseModel):

    __tablename__ = 'reddit_object_lists'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    date_created = Column(DateTime, default=datetime.now())
    list_type = Column(String, nullable=False)
    reddit_objects = relationship('RedditObject', secondary=list_association, backref='lists', lazy='dynamic')

    def __str__(self):
        return f'{self.list_type} List: {self.name}'


class RedditObject(BaseModel):

    __tablename__ = 'reddit_object'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    post_limit = Column(SmallInteger, default=25)
    avoid_duplicates = Column(Boolean, default=True)
    download_videos = Column(Boolean, default=True)
    download_images = Column(Boolean, default=True)
    download_comments = Column(Enum(CommentDownload), default=CommentDownload.do_not_download)
    download_comment_content = Column(Enum(CommentDownload), default=CommentDownload.do_not_download)
    download_nsfw = Column(Integer, default=0)  # -1 = exclude | 0 = include | 1 = only include
    date_added = Column(DateTime, default=datetime.now())
    lock_settings = Column(Boolean, default=False)
    absolute_date_limit = Column(DateTime, default=datetime.fromtimestamp(Const.FIRST_POST_EPOCH))
    date_limit = Column(DateTime, nullable=True)
    download_enabled = Column(Boolean, default=True)
    last_download = Column(DateTime, nullable=True)
    significant = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    inactive_date = Column(DateTime, nullable=True)
    post_sort_method = Column(String, default='NEW')
    download_naming_method = Column(Enum(DownloadNameMethod), default=DownloadNameMethod.title)
    subreddit_save_structure = Column(Enum(SubredditSaveStructure), default=SubredditSaveStructure.sub_name)
    new = Column(Boolean, default=True)

    object_type = Column(String(15))

    __mapper_args__ = {
        'polymorphic_identity': 'REDDIT_OBJECT',
        'polymorphic_on':  object_type,
    }

    def __str__(self):
        return f'{self.object_type}: {self.name}'

    def set_date_limit(self, epoch):
        """
        Tests the supplied epoch time to see if it is newer than the already established absolute date limit, and if so
        sets the absolute date limit to the time of the supplied epoch.
        :param epoch: A datetime in epoch seconds that should be the time of an extracted submission.
        """
        date_limit_epoch = self.absolute_date_limit.timestamp()
        if epoch > date_limit_epoch:
            self.absolute_date_limit = datetime.fromtimestamp(epoch)
            self.get_session().commit()

    def toggle_enable_download(self):
        self.download_enabled = not self.download_enabled
        self.get_session().commit()

    def get_post_count(self):
        return len(self.posts)

    def get_downloaded_posts(self):
        session = self.get_session()
        posts = session.query(Post).filter(Post.author == self)

    def get_non_downloaded_posts(self):
        pass

    def get_downloaded_comments(self):
        pass

    def get_downloaded_content(self):
        pass

    def get_non_downloaded_content(self):
        pass


class User(RedditObject):

    __tablename__ = 'user'

    id = Column(ForeignKey('reddit_object.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'USER',
    }


class Subreddit(RedditObject):

    __tablename__ = 'subreddit'

    id = Column(ForeignKey('reddit_object.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'SUBREDDIT',
    }


class DownloadSession(BaseModel):

    __tablename__ = 'download_session'

    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    extraction_thread_count = Column(Integer, nullable=True)
    download_thread_count = Column(Integer, nullable=True)

    def __str__(self):
        return f'DownloadSession: {self.id}'

    @property
    def duration(self):
        return SystemUtil.get_duration_str(self.start_time.timestamp(), self.end_time.timestamp())

    @property
    def duration_epoch(self):
        return self.start_time.timestamp() - self.end_time.timestamp()


class Post(BaseModel):

    __tablename__ = 'post'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    date_posted = Column(DateTime)
    domain = Column(String)
    score = Column(Integer)
    nsfw = Column(Boolean, default=False)
    reddit_id = Column(String)
    url = Column(String)

    extracted = Column(Boolean, default=False)
    extraction_date = Column(DateTime, nullable=True)
    extraction_error = Column(String, nullable=True)

    author_id = Column(ForeignKey('user.id'))
    author = relationship('User', backref='posts')
    subreddit_id = Column(ForeignKey('subreddit.id'))
    subreddit = relationship('Subreddit', backref='posts')
    download_session_id = Column(ForeignKey('download_session.id'))
    download_session = relationship('DownloadSession', backref='posts')  # session where the post was extracted

    def __str__(self):
        return f'Post: {self.title}'

    def set_extracted(self):
        self.extracted = True
        self.extraction_date = datetime.now()
        self.get_session().commit()

    def set_extraction_failed(self, message):
        self.extracted = False
        self.extraction_error = message
        self.get_session().commit()


class Comment(BaseModel):

    __tablename__ = 'comment'

    id = Column(Integer, primary_key=True)
    body = Column(String)
    body_html = Column(String)
    score = Column(Integer)
    date_added = Column(DateTime, default=datetime.now())
    date_posted = Column(DateTime)

    author_id = Column(ForeignKey('user.id'))
    author = relationship('User', backref='comments')
    subreddit_id = Column(ForeignKey('subreddit.id'))
    subreddit = relationship('Subreddit', backref='comments')
    post_id = Column(ForeignKey('post.id'))
    post = relationship('Post', backref='comments')
    parent_id = Column(ForeignKey('comment.id'), nullable=True)
    parent = relationship('Comment', remote_side=[id], backref='children')
    download_session_id = Column(ForeignKey('download_session.id'))
    download_session = relationship('DownloadSession', backref='comments')  # session where the comment was extracted

    def __str__(self):
        return f'Comment: {self.id}'


class Content(BaseModel):

    __tablename__ = 'content'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    download_title = Column(String, nullable=True)
    extension = Column(String)
    url = Column(String)
    directory_path = Column(String, nullable=True)

    downloaded = Column(Boolean, default=False)
    download_date = Column(DateTime, nullable=True)
    download_error = Column(String, nullable=True)

    user_id = Column(ForeignKey('user.id'))
    user = relationship('User', backref='content')
    subreddit_id = Column(ForeignKey('subreddit.id'))
    subreddit = relationship('Subreddit', backref='content')
    post_id = Column(ForeignKey('post.id'))
    post = relationship('Post', backref='content')
    download_session_id = Column(ForeignKey('download_session.id'), nullable=True)
    # The session in which this content was actually downloaded.  May differ from the parent post/comment
    # download_session if the content was unable to be downloaded during the same session, and was downloaded at a
    # later date.
    download_session = relationship('DownloadSession', backref='content')

    video_merge_id = None

    def __str__(self):
        return f'Content: {self.title}'

    @property
    def full_file_path(self):
        return os.path.join(self.directory_path, f'{self.download_title}.{self.extension}')

    def make_download_title(self):
        """Ensures each file name does not contain forbidden characters and is within the character limit"""
        # For some reason the file system (Windows at least) is having trouble saving files that are over 180ish
        # characters.  I'm not sure why this is, as the file name limit should be around 240. But either way, this
        # method has been adapted to work with the results that I am consistently getting.
        forbidden_chars = '"*\\/\'.|?:<>'
        filename = ''.join([x if x not in forbidden_chars else '#' for x in self.title])
        if len(filename) >= 176:
            filename = filename[:170] + '...'
        self.download_title = filename
        self.get_session().commit()

    def set_downloaded(self, download_session_id):
        self.download_session_id = download_session_id
        self.downloaded = True
        self.download_date = datetime.now()
        self.get_session().commit()

    def set_download_error(self, message):
        self.downloaded = False
        self.download_error = message
        self.get_session().commit()
