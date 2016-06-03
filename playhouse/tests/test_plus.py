# encoding=utf-8

import sys
import threading
try:
    from Queue import Queue
except ImportError:
    from queue import Queue

from peewee import OperationalError
from peewee import SqliteDatabase
from playhouse.tests.base import compiler
from playhouse.tests.base import database_class
from playhouse.tests.base import database_initializer
from playhouse.tests.base import ModelTestCase
from playhouse.tests.base import PeeweeTestCase
from playhouse.tests.base import query_db
from playhouse.tests.base import skip_unless
from playhouse.tests.base import test_db
from playhouse.tests.base import ulit
from playhouse.tests.models import *


class TestPlusQueries(ModelTestCase):
    requires = [User, Blog, Comment, Relationship, Component, Computer, EthernetPort]

    def setUp(self):
        self._orig_db = test_db
        kwargs = {}
        try:  # Some engines need the extra kwargs.
            kwargs.update(test_db.connect_kwargs)
        except:
            pass
        if isinstance(test_db, SqliteDatabase):
            # Put a very large timeout in place to avoid `database is locked`
            # when using SQLite (default is 5).
            kwargs['timeout'] = 30

        self.db = self.new_connection()
        self._orig_dbs = {}
        for tbl in self.requires:
            self._orig_dbs[tbl] = tbl._meta.database
            tbl._meta.database = self.db
        
        super(TestPlusQueries, self).setUp()

        user = User.create(username='username')
        user2 = User.create(username='username2')
        blog = Blog.create(user=user, title='title')
        comment = Comment.create(blog=blog, comment='comment')
        rel = Relationship.create(from_user=user, to_user=user2)
        
        hard_drive = Component.create(name='hard_drive')
        memory = Component.create(name='memory')
        processor = Component.create(name='processor')
        computer = Computer.create(hard_drive=hard_drive, memory=memory, processor=processor)
        ethernet_port = EthernetPort.create(computer=computer)

    def tearDown(self):
        for tbl, orig_db in self._orig_dbs.items():
          tbl._meta.database = orig_db
        test_db.close()
        super(TestPlusQueries, self).tearDown()

    def test_magic_all(self):
        with self.assertQueryCount(2):
          blog = Blog.ALL.get()
          self.assertEqual(list(Blog.ALL), [blog])
        
    def test_plus_basic(self):
        with self.assertQueryCount(1):
          blog = Blog.ALL.plus(Blog.user).get()
          self.assertEqual(blog.title, 'title')
          self.assertEqual(blog.user.username, 'username')
        
    def test_plus_two_deep(self):
        with self.assertQueryCount(1):
          comment = Comment.ALL.plus(Comment.blog, Blog.user).get()
          self.assertEqual(comment.blog.title, 'title')
          self.assertEqual(comment.blog.user.username, 'username')
        
    def test_plus_repeated_calls_do_nothing(self):
        with self.assertQueryCount(1):
          blog = Blog.ALL.plus(Blog.user).plus(Blog.user).get()
          self.assertEqual(blog.title, 'title')
          self.assertEqual(blog.user.username, 'username')
        
    def test_plus_fk_to_same_table(self):
        with self.assertQueryCount(1):
          rel = Relationship.ALL \
              .plus(Relationship.from_user) \
              .plus(Relationship.to_user) \
              .get()
          self.assertEqual(rel.from_user.username, 'username')
          self.assertEqual(rel.to_user.username, 'username2')
          
    def test_plus_fk_to_same_table_one_layer_in(self):
        with self.assertQueryCount(1):
          ethernet_port = EthernetPort.ALL \
              .plus(EthernetPort.computer, Computer.hard_drive) \
              .plus(EthernetPort.computer, Computer.memory) \
              .plus(EthernetPort.computer, Computer.processor) \
              .get()
          self.assertEqual(ethernet_port.computer.hard_drive.name, 'hard_drive')
          self.assertEqual(ethernet_port.computer.memory.name, 'memory')
          self.assertEqual(ethernet_port.computer.processor.name, 'processor')
          

