# -*- coding: utf-8 -*-

import random
import unittest
from flask import Flask
from funnel import *
from funnel.models import (db, Profile, ProposalSpace, Event, User, SyncTicket, Participant, TicketClient, TicketType)
from .event_models_fixtures import event_ticket_types, ticket_list, ticket_list2

app = Flask(__name__)
db.init_app(app)


def bulk_upsert(space, event_list):
    for event_dict in event_list:
        event = Event.upsert(space, Event.name_from_title(space, event_dict.get('title')),
            title=event_dict.get('title'), proposal_space=space)
        for ticket_type_title in event_dict.get('ticket_types'):
            ticket_type = TicketType.upsert(space, TicketType.name_from_title(space, ticket_type_title), proposal_space=space, title=ticket_type_title)
            event.ticket_types.append(ticket_type)


class TestEventModels(unittest.TestCase):
    app = app

    def setUp(self):
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        init_for('test')
        db.create_all()
        # Initial Setup
        random_user_id = random.randint(1, 1000)
        self.user = User(userid=unicode(random_user_id), username=u'lukes{userid}'.format(userid=random_user_id), fullname=u"Luke Skywalker",
            email=u'luke{userid}@dagobah.org'.format(userid=random_user_id))

        db.session.add(self.user)
        db.session.commit()

        self.profile = Profile(title='SpaceCon', userid=self.user.userid)
        db.session.add(self.profile)
        db.session.commit()

        self.space = ProposalSpace(title='2015', tagline='In a galaxy far far away...', profile=self.profile, user=self.user)
        db.session.add(self.space)
        db.session.commit()

        self.ticket_client = TicketClient(name="test client", client_eventid='123', clientid='123', client_secret='123', client_access_token='123', proposal_space=self.space)
        db.session.add(self.ticket_client)
        db.session.commit()

        bulk_upsert(self.space, event_ticket_types)
        db.session.commit()

        self.session = db.session

    def tearDown(self):
        self.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_import_from_list(self):
        # test bookings
        self.ticket_client.import_from_list(self.space, ticket_list)
        self.assertEquals(SyncTicket.query.count(), 3)
        self.assertEquals(Participant.query.count(), 3)
        p1 = Participant.query.filter_by(email='participant1@gmail.com', proposal_space=self.space).one_or_none()
        p2 = Participant.query.filter_by(email='participant2@gmail.com', proposal_space=self.space).one_or_none()
        self.assertEquals(len(p1.events), 2)
        self.assertEquals(len(p2.events), 1)

        # test cancellations
        cancel_list = [SyncTicket.get(self.space, 'o2', 't2')]
        self.ticket_client.import_from_list(self.space, ticket_list, cancel_list=cancel_list)
        self.assertEquals(len(p2.events), 0)

        # test_transfers
        self.ticket_client.import_from_list(self.space, ticket_list2)
        self.assertEquals(len(p2.events), 1)
        self.assertEquals(p2.events[0], Event.get(self.space, 'spacecon'))