#!/usr/bin/python
# 
# This file is part of the Lampadas Documentation System.
# 
# Copyright (c) 2000, 2001, 2002 David Merrill <david@lupercalia.net>.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# 
"""
Lampadas Session Manager Module

This module tracks users who have active sessions.
"""

from Globals import *
from BaseClasses import *
from Config import config
from Database import db
from Log import log
import Cookie

from CoreDM import dms

# WARNING: Whenever the sessions.session property is set, which identifies the
# currently logged-on user's session, the sessions.session.user attribute
# must also be set. You can't have a session without a user!
# 
class Sessions(LampadasCollection):
    """
    All users with currently active sessions.

    """

    def __init__(self):
        super(Sessions, self).__init__()
        self.load()

    def load(self):
        sql = 'SELECT username, ip_address, uri, created FROM session'
        cursor = db.select(sql)
        while (1):
            row = cursor.fetchone()
            if row==None: break
            session = Session()
            session.username   = trim(row[0])
            session.ip_address = trim(row[1])
            session.uri        = trim(row[2])
            session.created    = time2str(row[3])
            self[session.username] = session
    
    def add(self, username, ip_address, uri=''):
        sql = 'INSERT INTO session(username, ip_address, uri) VALUES (' + wsq(username) + ', ' + wsq(ip_address) + ', ' + wsq(uri) + ')'
        db.runsql(sql)
        db.commit()
        self[username] = Session(username)
        state.session = self[username]
        state.user = dms.username.get_by_id(username)

    def delete(self, username):
        sql = 'DELETE FROM session WHERE username=' + wsq(username)
        db.runsql(sql)
        db.commit()
        del self[username]
        state.session = None
        state.user = None

    def count(self):
        return db.read_value('SELECT COUNT(*) FROM session')

    def get_session(self, req):
        state.session = None
        state.user = None
        cookie = self.get_cookie(req.headers_in, 'lampadas')
        if cookie:
            session_id = str(cookie)
            sql = 'SELECT username FROM username WHERE session_id=' + wsq(session_id)
            cursor = db.select(sql)
            row = cursor.fetchone()
            if not row==None:
                username = trim(row[0])
                self.load()
                if self.has_key(username):
                    state.session = self[username]
                    state.session.refresh(req.connection.remote_addr[0], req.uri)
                    state.user = state.session.user
                else:
                    self.add(username, req.connection.remote_addr[0], req.uri)
                state.user = dms.username.get_by_id(username)

    def get_cookie(self, headers_in, key):
        if headers_in.has_key('Cookie'):
            cookie = Cookie.SmartCookie(headers_in['Cookie'])
            cookie.load(headers_in['Cookie'])
            if cookie.has_key(key):
                return cookie[key].value
        return None

class Session:

    def __init__(self, username=None):
        self.user = None
        if username:
            self.user = dms.username.get_by_id(username)
            sql = 'SELECT username, ip_address, uri, created FROM session WHERE username=' + wsq(username)
            cursor = db.select(sql)
            row = cursor.fetchone()
            if row:
                self.username   = trim(row[0])
                self.ip_address = trim(row[1])
                self.uri        = trim(row[2])
                self.created    = time2str(row[3])
                
    def refresh(self, ip_address, uri=''):
        sql = 'UPDATE session SET updated=now(), ip_address=' + wsq(ip_address) + ', uri=' + wsq(uri) + ' WHERE username=' + wsq(self.username)
        updated = db.runsql(sql)
        db.commit()
        if updated==0:
            log(3, self.username + '\'s session expired, recreating it.')
            sql = 'INSERT INTO session(username) VALUES (' + wsq(self.username) + ')'
            db.runsql(sql)
            db.commit()

sessions = Sessions()

# main
if __name__=='__main__' :
    print "Running unit tests..."
    print "End unit test run."
    
