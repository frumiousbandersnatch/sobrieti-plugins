###
# encoding=utf-8
# Copyright (c) 2010, Muxy
# All rights reserved.
#
#
###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import random

TC_NONE = 0
TC_RUEBDPL = 1
TC_GARE = 2
TC_COMPANY = 3
TC_CARD = 4
TC_PAY = 5
TC_PRISON = 6
TC_GOTO = 7
TC_RIEN = 8
TC_VISITE = 9
TC_COLLECT = 10
TC_JAIL_EXIT = 11
TC_COLLECTPLAYER = 12
TC_PAYPLAYER = 13
TC_REPAIR = 14
TC_PAYCHANCE = 15
TC_MOVE_FW = 16
TC_MOVE_BK = 17
TC_MOVE_NEXT = 18
TC_MOVE_PREV = 19
TC_MOVE_COUNT = 20

TM_COUNT = 0
TM_FW = 1
TM_BK = 2
TM_NEXT = 3
TM_PREV = 4

class PolyCase:
    pass

class PolyCard:
    name = ""
    typecard = 0
    money = 0
    goto = PolyCase
    typenext = 0
    movecount = 0

    def __init__( self, pname, ptypecard, param ):
        self.name = pname
        self.typecard = ptypecard
        self.money = 0
        self.goto = PolyCase
        self.typenext = 0
        self.movecount = 0
        l_sDisplay = "name %s, type %d, param %s" % (pname, ptypecard, param)
        if (ptypecard == TC_GOTO or ptypecard == TC_MOVE_FW or ptypecard == TC_MOVE_BK):
            self.goto = param
        elif (ptypecard == TC_MOVE_NEXT or ptypecard == TC_MOVE_PREV):
            self.typenext = param
        elif (ptypecard == TC_MOVE_COUNT):
            self.movecount = param
        elif (ptypecard == TC_COLLECT or ptypecard == TC_PAY or ptypecard == TC_COLLECTPLAYER or ptypecard == TC_PAYPLAYER):
            self.money = param
            l_sDisplay = "Init money %d" % ( self.money )

    def docard( self, case, player, irc ):
        irc.reply( "%s" % (self.name) )
        if (self.typecard == TC_MOVE_FW or self.typecard == TC_MOVE_BK):
            irc.reply( "moving to %s" % (self.goto.name) )
            case.leave( player, irc )
            if (self.typecard == TC_MOVE_FW):
                case.next.move( player, TM_FW, self.goto, irc )
            elif (self.typecard == TC_MOVE_BK):
                case.previous.move( player, TM_BK, self.goto, irc )
        elif (self.typecard == TC_MOVE_NEXT):
            irc.reply( "moving to next %s" % (self.typenext) )
            case.leave( player, irc )
            case.next.move( player, TM_NEXT, self.typenext, irc )
        elif (self.typecard == TC_MOVE_PREV):
            irc.reply( "moving to previous %s" % (self.typenext) )
            case.leave( player, irc )
            case.previous.move( player, TM_PREV, self.typenext, irc )
        elif (self.typecard == TC_MOVE_COUNT ):
            irc.reply( "moving %d square" % (self.movecount) )
            case.leave( player, irc )
            if (self.movecount > 0 ):
                case.next.move( player, TM_COUNT, self.movecount-1, irc )
            else:
                case.previous.move( player, TM_COUNT, self.movecount+1, irc )
        elif (self.typecard == TC_COLLECT):
            player.moneyreceive( self.money )
            irc.reply( "You collect %d and you have %d" % (self.money, player.money) )
        elif (self.typecard == TC_PAY):
            player.moneypay( self.money )
            irc.reply( "You pay %d and you have %d" % (self.money, player.money) )
        elif (self.typecard == TC_GOTO):
            case.leave( player, irc )
            self.goto.enter( player, irc )
        elif (self.typecard == TC_COLLECTPLAYER):
            collected = 0
            for eachplayer in player.players:
                if (eachplayer != player):
                    collected += self.money
                    player.moneyreceive( self.money )
                    eachplayer.moneypay( self.money )
                    irc.reply( "You receive %d from %s" % (self.money, eachplayer.name), private=True, notice=True )
                    irc.reply( "You give %d to %s" % (self.money, player.name ), to=eachplayer.name, private=True, notice=True )
            irc.reply( "You have collected %d for your birthday !" % (collected ) )
        elif (self.typecard == TC_PAYPLAYER):
            paid = 0
            for eachplayer in player.players:
                if (eachplayer != player):
                    paid += self.money
                    player.moneypay( self.money )
                    eachplayer.moneyreceive( self.money )
                    irc.reply( "You give %d to %s" % (self.money, eachplayer.name), private=True, notice=True )
                    irc.reply( "You receive %d from %s" % (self.money, player.name ), to=eachplayer.name, private=True, notice=True )
            irc.reply( "You have paid %d for your election !" % (paid ) )
        else:
            irc.reply( "Card Action %d not programmed !" % (self.typecard) )

class PolyCards:
    cards = []
    position = 0
    name = ""

    def __init__( self, name ):
        self.name = name
        self.position = 0
        self.cards = []

    def addcase( self, case ):
        self.cases.append( case )

    def mix( self ):
        cards = []
        while ( len(self.cards)>0 ):
            card = self.cards[random.randrange(0,len(self.cards))]
            cards.append( card )
            self.cards.remove( card )
        self.cards = cards
        self.position = 0

    def docard( self, case, player, irc ):
        self.pioche( ).docard( case, player, irc )

    def display( self, irc ):
        for card in self.cards:
            #irc.reply( "%s %s %d" % (self.name, card.name, card.money) )
            irc.reply( "%s: %s" % (self.name, card.name) )

    def pioche( self ):
        card = self.cards[self.position]
        self.position += 1
        self.position %= len(self.cards)
        return card


class PolyPlayer:
    position = 0 #PolyCase
    automove = False
    name = ""
    money = 1500
    jailturn = 0
    housecount = 0
    hotelcount = 0
    dices = 0
    through = []
    groups = []
    players = []

    def __init__( self, name ):
        self.name = name
        self.money = 1500
        self.position = PolyCase
        self.jailturn = 0
        self.stationowned = 0
        self.companyowned = 0
        self.housecount = 0
        self.hotelcount = 0
        self.automove = False
        self.dices = 0
        self.through = []
        self.groups = []
        self.players = []
        self.groups.append( PolyGroup( "110", 50, 2, True ) )
        self.groups.append( PolyGroup( "120", 50, 3, True ) )
        self.groups.append( PolyGroup( "210", 100, 3, True ) )
        self.groups.append( PolyGroup( "220", 100, 3, True ) )
        self.groups.append( PolyGroup( "310", 150, 3, True ) )
        self.groups.append( PolyGroup( "320", 150, 3, True ) )
        self.groups.append( PolyGroup( "410", 200, 3, True ) )
        self.groups.append( PolyGroup( "420", 200, 2, True ) )
        self.groups.append( PolyGroup( "station", 0, 4, False ) )
        self.groups.append( PolyGroup( "service", 0, 2, False ) )

    def move( self, p_nCase, irc ):
        #deplace le joueur de case en case...
        #quitte la case où l'on est
        irc.reply( "moves %d squares" % (p_nCase) )
        self.through = []
        self.position.leave( self, irc )
        if (p_nCase > 0):
            self.position.next.move( self, TM_COUNT, p_nCase - 1, irc )
        elif (p_nCase < 0):
            self.position.previous.move( self, TM_COUNT, p_nCase + 1, irc )
        else:
            self.position.enter( self, irc )

    def gothrough( self, message ):
        self.through.append( message )

    def displaythrough( self, irc ):
        if (len( self.through ) > 0):
            display = "You go through "
            for message in self.through:
                display += "%s, " % (message)
            irc.reply( display )
            self.through = []

    def display_info( self, irc ):
        irc.reply( "player %s, position %s, money %d, jailturn %d" % (self.name, self.position.name, self.money, self.jailturn) )
        for group in self.groups:
            irc.reply( "%s - count owned %d - ownall %d" % (group.info( ), self.countowned( group.name ), self.ownall( group.name) ) )

    def countowned( self, groupname ):
        count = 0
        for group in self.groups:
            if (group.name == groupname):
                count = group.owned
        return count

    def ownall( self, groupname ):
        ownall = False
        for group in self.groups:
            if (group.name == groupname):
                ownall = group.ownall
        return ownall

    def buyingroup( self, groupname ):
        for group in self.groups:
            if (group.name == groupname):
                group.owned += 1
                if (group.owned == group.propcount):
                    group.ownall = True

    def moneycanpay( self, amount ):
        canpay = False
        if (amount <= self.money):
            canpay = True
        return canpay

    def moneypay( self, amount ):
        self.money -= amount

    def moneyreceive( self, amount ):
        self.money += amount

class PolyBoard:
    start = PolyCase
    jail = PolyCase
    freepark = PolyCase
    groups = []
    cases = []
    name = ""
    chance = PolyCards
    community = PolyCards

    def __init__( self, name ):
        self.name = name
        self.cases = []
        self.groups = []

        self.start = self.case_add( PolyCase( "Go", TC_PAY, "" ) )
        self.start.moneythrough = 200
        self.start.moneystop = self.start.moneythrough * 2

        self.jail = self.case_add( PolyCase( "In Jail", TC_PRISON, "" ) )

        self.community = PolyCards( "Community Chest" )

        self.community.cards.append( PolyCard( "Advance to Go and collect %s" % (self.start.moneystop), TC_MOVE_FW, self.start ) )
        self.community.cards.append( PolyCard( "Bank error in your favor - Collect 200", TC_COLLECT, 200 ) )
        self.community.cards.append( PolyCard( "Doctor's fees - Pay 50", TC_PAY, 50 ) )
        self.community.cards.append( PolyCard( "Get out of jail for free", TC_JAIL_EXIT, 50 ) )
        self.community.cards.append( PolyCard( "Go to Jail - Go directly to jail", TC_GOTO, self.jail ) )
        self.community.cards.append( PolyCard( "It's your birthday - Collect 10 from each player", TC_COLLECTPLAYER, 10 ) )
        self.community.cards.append( PolyCard( "Income Tax refund - Collect 20", TC_COLLECT, 20 ) )
        self.community.cards.append( PolyCard( "Life Insurance Matures - Collect 100", TC_COLLECT, 100 ) )
        self.community.cards.append( PolyCard( "Pay Hospital Fees of 100 - Pay 100", TC_PAY, 100 ) )
        self.community.cards.append( PolyCard( "Pay School Fees of 150 - Pay 150", TC_PAY, 150 ) )
        self.community.cards.append( PolyCard( "Receive 25 Consultancy Fee - Receive 25", TC_COLLECT, 25 ) )
        self.community.cards.append( PolyCard( "You are assessed for street repairs - 40 per house, 115 per hotel", TC_REPAIR, 0 ) )
        self.community.cards.append( PolyCard( "You have won seconde prize in a beauty contest - Collect 10", TC_COLLECT, 10 ) )
        self.community.cards.append( PolyCard( "You inherit 100", TC_COLLECT, 100 ) )
        self.community.cards.append( PolyCard( "From sale of stock you get 45", TC_COLLECT, 45 ) )
        self.community.cards.append( PolyCard( "Holiday Fund matures - Receive 100", TC_COLLECT, 100 ) )
        self.community.cards.append( PolyCard( "Pay a 10 fine or take a Chance", TC_PAYCHANCE, 10 ) )
        self.community.cards.append( PolyCard( "Pay your insurance premium", TC_PAY, 50 ) )

        self.chance = PolyCards( "Chance" )

        self.chance.cards.append( PolyCard( "Advance to Go - Collect %s" % (self.start.moneystop), TC_MOVE_FW, self.start ) )
        self.chance.cards.append( PolyCard( "Advance to nearest Utility. If unowed you may buy it from the Bank. If owned, throw dice and pay 10 times dices sum to owner", TC_MOVE_NEXT, TC_COMPANY ) )
        self.chance.cards.append( PolyCard( "Advance to nearest Rairoad and pay owner twice the rental. If unowned, you can buy it from the Bank", TC_MOVE_NEXT, TC_GARE ) )
        self.chance.cards.append( PolyCard( "Bank pays you dividend of 50", TC_COLLECT, 50 ) )
        self.chance.cards.append( PolyCard( "Get out of Jail free", TC_JAIL_EXIT, 50 ) )
        self.chance.cards.append( PolyCard( "Go back 3 spaces", TC_MOVE_COUNT, -3 ) )
        self.chance.cards.append( PolyCard( "Go directly to Jail - do not pass Go - dont collect %d" % (self.start.moneythrough), TC_GOTO, self.jail ) )
        self.chance.cards.append( PolyCard( "Make general repairs on all your property - for each house pay 25 - for each hotel pay 100", TC_REPAIR, [25, 100] ) )
        self.chance.cards.append( PolyCard( "Speeding Fine 15", TC_PAY, 15 ) )
        self.chance.cards.append( PolyCard( "You have been elected chairman of the board - pay each player 50", TC_PAYPLAYER, 50 ) )
        self.chance.cards.append( PolyCard( "You have won a crossword competition - collect 100", TC_COLLECT, 100 ) )
        self.chance.cards.append( PolyCard( "Drunk in charge fine 20", TC_PAY, 20 ) )

        case = self.case_add( PolyCase( "Mediterranean Avenue", TC_RUEBDPL, "110" ) )
        case.previous = self.start
        self.community.cards.append( PolyCard( "Go back to Mediterranean Avenue", TC_MOVE_BK, case ) )
        case.init_cost( [60, 2, 10, 30, 90, 160, 250] )
        previous = case
        self.start.next = case

        case = self.case_add( PolyCase( "Community Chest", TC_CARD, "Community" ) )
        case.card = self.community
        case.previous = previous
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Baltic Avenue", TC_RUEBDPL, "110" ) )
        case.previous = previous
        case.init_cost( [60, 4, 20, 60, 180, 320, 450] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Income Tax", TC_PAY, "" ) )
        case.previous = previous
        case.moneystop = -200
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Reading Railroad", TC_GARE, "station" ) )
        case.previous = previous
        self.chance.cards.append( PolyCard( "Take a trip to Reading Railroad - if you pass Go collect %d" % (self.start.moneythrough), TC_MOVE_FW, case ) )
        case.init_cost( [200, 25, 50, 100, 200] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Oriental Avenue", TC_RUEBDPL, "120" ) )
        case.previous = previous
        case.init_cost( [100, 6, 30, 90, 270, 400, 550] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Chance", TC_CARD, "chance" ) )
        case.card = self.chance
        case.previous = previous
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Vermont Avenue", TC_RUEBDPL, "120" ) )
        case.previous = previous
        case.init_cost( [100, 6, 30, 90, 270, 400, 550] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Connecticut Avenue", TC_RUEBDPL, "120" ) )
        case.previous = previous
        case.init_cost( [120, 8, 40, 100, 300, 450, 600] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Visit Only", TC_VISITE, "" ) )
        case.previous = previous
        case.goto = self.jail
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "St. Charles Place", TC_RUEBDPL, "210" ) )
        case.previous = previous
        self.chance.cards.append( PolyCard( "Advance to St Charles Place - if you pass Go, collect %d" % (self.start.moneythrough), TC_MOVE_FW, case ) )
        case.init_cost( [140, 10, 50, 150, 450, 625, 750] )
        previous.next = case
        previous = case

        self.jail.next = case

        case = self.case_add( PolyCase( "Electric Company", TC_COMPANY, "service" ) )
        case.previous = previous
        case.init_cost( [150, 4, 10] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "States Avenue", TC_RUEBDPL, "210" ) )
        case.previous = previous
        case.init_cost( [140, 10, 50, 150, 450, 625, 750] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Virginia Avenue", TC_RUEBDPL, "210" ) )
        case.previous = previous
        case.init_cost( [160, 12, 60, 180, 500, 700, 900] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Pennsylvania Railroad", TC_GARE, "station" ) )
        case.previous = previous
        case.init_cost( [200, 25, 50, 100, 200] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "St. James Place", TC_RUEBDPL, "220" ) )
        case.previous = previous
        case.init_cost( [180, 14, 70, 200, 550, 750, 950] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Community Chest", TC_CARD, "community" ) )
        case.card = self.community
        case.previous = previous
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Tenessee Avenue", TC_RUEBDPL, "220" ) )
        case.previous = previous
        case.init_cost( [180, 14, 70, 200, 550, 750, 950] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "New York Avenue", TC_RUEBDPL, "220" ) )
        case.previous = previous
        case.init_cost( [200, 16, 80, 220, 600, 800, 1000] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Free Parking", 0, "" ) )
        case.previous = previous
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Kentucky Avenue", TC_RUEBDPL, "310" ) )
        case.previous = previous
        case.init_cost( [220, 18, 90, 250, 700, 875, 1050] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Chance", TC_CARD, "Chance" ) )
        case.card = self.chance
        case.previous = previous
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Indiana Avenue", TC_RUEBDPL, "310" ) )
        case.previous = previous
        case.init_cost( [220, 18, 90, 250, 700, 875, 1050] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Illinois Avenue", TC_RUEBDPL, "310" ) )
        case.previous = previous
        self.chance.cards.append( PolyCard( "Advance to Illinois Avenue", TC_MOVE_FW, case  ) )
        case.init_cost( [240, 20, 90, 300, 750, 925, 1100] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "B. & O. Railroad", TC_GARE, "station" ) )
        case.previous = previous
        case.init_cost( [200, 25, 50, 100, 200] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Atlantic Avenue", TC_RUEBDPL, "320" ) )
        case.previous = previous
        case.init_cost( [260, 22, 110, 330, 800, 975, 1150] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Ventnor Avenue", TC_RUEBDPL, "320" ) )
        case.previous = previous
        case.init_cost( [260, 22, 110, 330, 800, 975, 1150] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Water Works", TC_COMPANY, "service" ) )
        case.previous = previous
        case.init_cost( [150, 4, 10] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Marvin Garden", TC_RUEBDPL, "320" ) )
        case.previous = previous
        case.init_cost( [280, 24, 120, 360, 850, 1025, 1200] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Go to Jail", TC_GOTO, "" ) )
        case.previous = previous
        case.goto = self.jail
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Pacific Avenue", TC_RUEBDPL, "410" ) )
        case.previous = previous
        case.init_cost( [300, 26, 130, 390, 900, 1100, 1275] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "North Carolina Avenue", TC_RUEBDPL, "410" ) )
        case.previous = previous
        case.init_cost( [300, 26, 130, 390, 900, 1100, 1275] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Community Chest", TC_CARD, "community" ) )
        case.card = self.community
        case.previous = previous
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Pennsylvania Avenue", TC_RUEBDPL, "410" ) )
        case.previous = previous
        case.init_cost( [320, 28, 150, 450, 1000, 1200, 1400] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Short Line", TC_GARE, "station" ) )
        case.previous = previous
        case.init_cost( [200, 25, 50, 100, 200] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Chance", TC_CARD, "chance" ) )
        case.card = self.chance
        case.previous = previous
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Park Place", TC_RUEBDPL, "420" ) )
        case.previous = previous
        case.init_cost( [350, 35, 175, 500, 1100, 1300, 1500] )
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Luxury Tax", TC_PAY, "" ) )
        case.previous = previous
        case.moneystop = -75
        previous.next = case
        previous = case

        case = self.case_add( PolyCase( "Boardwalk", TC_RUEBDPL, "420" ) )
        case.previous = previous
        self.chance.cards.append( PolyCard( "Advance to Boardwalk", TC_MOVE_FW, case ) )
        case.init_cost( [400, 50, 200, 600, 1400, 1700, 2000] )
        previous.next = case

        case.next = self.start
        self.start.previous = case

    def display( self, irc ):
        for case in self.cases:
            if (case.owner == PolyPlayer):
                irc.reply( "%s" % (case.name) )
            else:
                irc.reply( "%s owned by %s" % (case.name, case.owner.name) )

    def case_add( self, case ):
        self.cases.append( case )
        return case

    def group_add( self, group ):
        self.groups.append( group )
        return group

    def init_cases( self ):
        for case in self.cases:
            case.init_case( )

class PolyGroup:
    name = ""
    housecost = 0
    owned = 0
    ownall = False
    propcount = 0
    canbuild = False

    def __init__( self, name, housecost, propcount, canbuild ):
        self.name = name
        self.housecost = housecost
        self.propcount = propcount
        self.canbuild = canbuild

    def case_add( self, case ):
        case.group = self
        self.cases.append( case )

    def info( self ):
        l_sDisplay = "Group %s, housecost %d, owned %d, Own all %d" % (self.name, self.housecost, self.owned, self.ownall )
        return l_sDisplay

class PolyCase:
    name = ""
    next = PolyCase
    previous = PolyCase
    owner = PolyPlayer
    group = ""
    card = PolyCards
    players = []
    goto = PolyCase
    typecase = 0
    moneystop = 0
    moneythrough = 0
    landcount = 0
    throughcount = 0
    housecount = 0
    hotelcount = 0
    #cost rent empty, 1 house, 2, 3, 4, Hotel
    cost = [0, 0, 0, 0, 0, 0]

    def __init__( self, name, p_type, group ):
        self.name = name
        self.next = PolyCase
        self.previous = PolyCase
        self.owner = PolyPlayer
        self.players = []
        self.typecase = p_type
        self.housecount = 0
        self.hotelcount = 0
        self.group = group

    def init_case( self ):
        self.owner = PolyPlayer
        self.players = []
        self.landcount = 0
        self.throughcount = 0
        self.housecount= 0
        self.hotelCount = 0

    def init_player( self, player, irc ):
        irc.reply( "you've been teleported to %s square" % (self.name) )
        self.players.append( player )
        player.position = self

    def init_cost( self, cost ):
        self.cost = cost

    def buy( self, player, irc ):
        if (self.owner == PolyPlayer ):
            player.money -= self.cost[0]
            irc.reply( "%s (%s) bought for %d, %d remaining" % (self.name, self.group, self.cost[0], player.money ) )
            self.owner = player
            player.buyingroup( self.group )
            if (self.typecase == TC_RUEBDPL):
                if (player.ownall( self.group )):
                    irc.reply( "All properties owned, you can start to build" )

    def leave( self, p_player, irc ):
        irc.reply( "you leave %s" % (self.name) )
        self.players.remove( p_player )
        p_player.posion = PolyCase
        if (self.typecase==TC_PRISON):
            p_player.jailturn = 0

    def enter( self, player, irc ):
        irc.reply( "you land on %s" % (self.name) )
        self.landcount += 1
        if (self.typecase == TC_GOTO):
            self.goto.enter( player, irc )
        else:
            self.players.append( player )
            player.position = self

        if (self.typecase == TC_RUEBDPL or self.typecase == TC_GARE or self.typecase == TC_COMPANY):
            if (self.owner == PolyPlayer):
                irc.reply( "%s has no owner you can buy it for %d and you have %d" % (self.name, self.cost[0], player.money ) )
                if ( player.money >= self.cost[0] ):
                    irc.reply( "Enough money, automatic buy" )
                    self.buy( player, irc )
            elif (self.owner == player):
                irc.reply( "it's good to be at home" )
            else:
                # search for rent cost when street
                if (self.typecase == TC_RUEBDPL ):
                    if (self.housecount == 0 and self.hotelcount == 0):
                        irc.reply( "%s (%s) owned by %s, count %d, all %d" % (self.name, self.group, self.owner.name, self.owner.countowned( self.group ), self.owner.ownall( self.group ) ) )
                        if (self.owner.ownall( self.group)):
                            rent = self.cost[1]*2
                            l_sOutput = "%s is owned by %s - all group %s owned - no house - no hotel - inital rent is %d x 2 = %d" % (self.name, self.owner.name, self.group, self.cost[1], rent )
                        else:
                            rent = self.cost[1]
                            l_sOutput = "%s is owned by %s - no house - no hotel rent is %d" % (self.name, self.owner.name, rent )
                    elif (self.housecount > 0 ):
                        rent = self.cost[1 + self.housecount]
                        l_sOutput = "%s is owned by %s - %d houses rent is %d" % (self.name, self.owner.name, rent )
                    elif (self.hotelcount > 0 ):
                        rent = self.cost[1 + self.hotelcount]
                        l_sOutput = "%s is owned by %s - %d hotel rent is %d" % (self.name, self.owner.name, rent )
                elif (self.typecase == TC_GARE ):
                    rent = self.cost[self.owner.countowned(self.group)]
                    l_sOutput = "%s (%s) is owned by %s, rent is %d - %d station owned" % ( self.name, self.group, self.owner.name, self.cost[self.owner.countowned(self.group)], self.owner.countowned(self.group) )
                elif (self.typecase == TC_COMPANY):
                    rent = player.dices * self.cost[self.owner.countowned(self.group)]
                    l_sOutput = "%s is owned by %s, rent is %d x dices sum (%d) = %d" % ( self.name, self.owner.name, self.cost[self.owner.countowned(self.group)], player.dices, player.dices * self.cost[self.owner.countowned(self.group)] )
                irc.reply( l_sOutput )
                player.money -= rent
                irc.reply( "You pay %d to %s" % (rent, self.owner.name), private=True, notice=True )
                self.owner.money += rent
                irc.reply( "You receive %d from %s" % (rent, player.name), to=self.owner.name, private=True, notice=True )

        if (self.typecase == TC_PAY ):
            if (self.moneystop > 0):
                s_display = "you receive %s"
            else:
                s_display = "you pay %d"
            irc.reply( s_display % (abs(self.moneystop)) )
            player.money += self.moneystop

        if (self.typecase == TC_PRISON):
            irc.reply( "Welcome %s" % (self.name) )
            player.jailturn = 0
        elif (self.typecase == TC_VISITE):
            irc.reply( "Visiting Jail..." )
            if (len(self.goto.players)>0):
                for jailplayer in self.goto.players:
                    irc.reply( "visiting [%s]" % (jailplayer.name) )
            else:
                irc.reply( "nobody to visit" )

        if (self.typecase == TC_CARD):
            self.card.docard( self, player, irc )

    def move( self, player, typemove, param, irc ):
        #check if we are not arrived TM_COUNT, TM_SQUARE, TM_NEXT
        arrived = False
        """
        if (typemove == TM_FW or typemove == TM_BK):
            irc.reply( "target is %s" % (param.name) )
        if (typemove == TM_COUNT):
            irc.reply( "TM_COUNT remain %d" % (param) )
        """

        if (typemove == TM_COUNT and param == 0):
            arrived = True
        if ((typemove == TM_FW or typemove == TM_BK) and param == self ):
            arrived = True
        if ((typemove == TM_NEXT or typemove == TM_PREV) and param == self.typecase):
            arrived = True

        if (arrived):
            # arrived, display all through
            player.displaythrough( irc )
            # enter the square
            self.enter( player, irc )
        else:
            #not arrived go through current square
            self.throughcount += 1
            player.gothrough( self.name )
            # check for money through
            if ( self.typecase == TC_PAY and self.moneythrough != 0):
                if (self.moneythrough > 0):
                    s_display = "you receive %s"
                else:
                    s_display = "you pay %d"
                player.gothrough( s_display % (abs(self.moneythrough)) )
                player.money += self.moneythrough
            # go to next square
            if (typemove == TM_COUNT):
                #next or previous according to param sign
                if (param > 0):
                    self.next.move( player, typemove, param-1, irc )
                else:
                    self.previous.move( player, typemove, param+1, irc )
            elif (typemove == TM_FW or typemove == TM_NEXT):
                self.next.move( player, typemove, param, irc )
            elif (typemove == TM_BK or typemove == TM_PREV):
                self.previous.move( player, typemove, param, irc )


class PythonPoly(callbacks.Plugin):
    """Add the help for "@plugin help PythonPoly" here
    This should describe *how* to use this plugin."""

    players = []
    board = PolyBoard( "Python Poly" )
    game_started = False
    next_player = 0
    dice1 = 0
    dice2 = 0
    rolled = False
    can_roll_again = False
    double_count = 0
    moved = True
    player = PolyPlayer

    def gamestarted( self, irc ):
        if (not self.game_started):
            irc.reply( "Game No Started" )
        return self.game_started

    def poly( self, irc, msg, args ):
        """ [poly command]
        init: re-init the game,
        players : display player list,
        play : add your nick to the player list,
        info : display information on your player nick,
        noplay : remove your nick from the player list,
        roll : roll the dices,
        move : move your nick on the board,
        end : end the turn and give dices to next player,
        """
        irc.reply( "Welcome to PythonPoly game", prefixNick=False )
        if ( len(args) > 0 ):
            # get the current player
            if (self.game_started):
                self.player = self.players[self.next_player]
                self.player.players = self.players

            l_sAction = args[0]

            if ( l_sAction == "help" ):
                pass

            if ( l_sAction == "chance" ):
                if self.gamestarted( irc ):
                    l_sSubAction = ""
                    if ( len(args) > 1 ):
                        l_sSubAction = args[1]
                    if (l_sSubAction == ""):
                        # irc.reply( "Chance card %s" % ( self.board.chance.pioche( ).name ) )
                        self.board.chance.docard( self.players[self.next_player].position, self.players[self.next_player], irc )
                    elif (l_sSubAction == "pos"):
                        irc.reply( "Chance position %d" % (self.board.chance.position) )
                    elif (l_sSubAction == "mix" ):
                        self.board.chance.mix( )
                        irc.reply( "Cards mixed" )
                    elif (l_sSubAction == "display" ):
                        self.board.chance.display( irc )
                    elif (l_sSubAction == "next" ):
                        irc.reply( "Card is %s" % (self.board.chance.pioche( ).name) )

            if ( l_sAction == "community" ):
                if self.gamestarted( irc ):
                    l_sSubAction = ""
                    if ( len(args) > 1 ):
                        l_sSubAction = args[1]
                    if (l_sSubAction == ""):
                        self.board.community.docard( self.players[self.next_player].position, self.players[self.next_player], irc )
                    elif (l_sSubAction == "pos"):
                        irc.reply( "Community position %d" % (self.board.community.position) )
                    elif (l_sSubAction == "mix" ):
                        self.board.community.mix( )
                        irc.reply( "Cards mixed" )
                    elif (l_sSubAction == "display" ):
                        self.board.community.display( irc )
                    elif (l_sSubAction == "next"):
                        irc.reply( "Community card %s" % ( self.board.community.pioche( ).name ) )

            if ( l_sAction=="init" ):
                if ( msg.nick in irc.state.channels[msg.args[0]].ops ):
                    irc.reply( "Reseting player position" )
                    for player in self.players:
                        player.position.leave( player, irc )
                    self.players = []
                    self.game_started = False
                    self.rolled = False
                    self.moved = True
                    self.can_roll_again = False
                    self.double_count = 0
                    irc.reply( "Reseting board" )
                    self.board.init_cases( )
                    irc.reply( "mixing cards" )
                    self.board.community.mix( )
                    self.board.chance.mix( )
                    next_player = 0
                    irc.reply( "Game ready" )
                else:
                    irc.reply( "only channel operator can use an init command" )

            if ( l_sAction=="start" ):
                if ( len( self.players ) > 0 ):
                    if ( not self.game_started):
                        self.next_player = random.randrange(0,len(self.players))
                        irc.reply( "player %d will start" % (self.next_player) )
                        irc.reply( "Game starts, first player is %s" % (self.players[self.next_player].name) )
                        self.game_started = True
                    else:
                        irc.reply( "Game already started" )
                else:
                    irc.reply( "Player list is empty" )

            if ( l_sAction=="play" ):
                # add nick as player into the player list
                # check if player already exists in list
                if ( not self.game_started ):
                    can_play = True
                    for player in self.players:
                        if (player.name==msg.nick):
                           can_play = False
                    if ( can_play ):
                        new_player = PolyPlayer( msg.nick )
                        self.players.append( new_player )
                        irc.reply( "You have been added to the player list" )
                        self.board.start.init_player( new_player, irc )
                        new_player.autmove = True
                    else:
                        irc.reply( "Hey Stupid, you are already on the list" )
                else:
                    irc.reply( "Game started - Comme back later" )

            if ( l_sAction=="noplay" ):
                for player in self.players:
                    if ( player.name == msg.nick ):
                        self.players.remove( player )
                        irc.reply( "You have been removed from the player list" )

            if ( l_sAction=="players" ):
                if (len( self.players ) == 0):
                    irc.reply( "The player list is empty !" )
                else:
                    for player in self.players:
                        irc.reply( "%s is on %s and has money %d" % (player.name, player.position.name, player.money) )

            if ( l_sAction=="roll" ):
                if ( self.game_started ):
                    can_play = False
                    for player in self.players:
                        if (player.name == msg.nick ):
                            can_play = True
                    if ( can_play ):
                        if ( msg.nick == self.player.name ):
                            if ( ( not self.rolled or self.can_roll_again ) and self.moved ):
                                irc.reply( "Rolls the dices for %s ..." %(msg.nick), action=True )
                                self.rolled = True
                                if ( msg.nick in irc.state.channels[msg.args[0]].ops and len(args) == 3 ):
                                    self.dice1 = int(args[1])
                                    self.dice2 = int(args[2])
                                else:
                                    self.dice1 = random.randrange( 0, 6 ) + 1
                                    self.dice2 = random.randrange( 0, 6 ) + 1
                                self.can_roll_again = False
                                self.moved = False
                                if (self.dice1 == self.dice2):
                                    self.double_count += 1
                                    if (player.position.typecase != TC_PRISON):
                                        self.can_roll_again = True
                                irc.reply( "result is %d & %d" % (self.dice1, self.dice2) )
                                if (self.double_count ==  3):
                                    irc.reply( "double count = 3, Go to Jail" )
                                    self.can_roll_again = False
                                self.player.dices = self.dice1 + self.dice2
                                l_sAction = "move"
                            else:
                                irc.reply( "dices already rolled" )
                        else:
                            irc.reply("this is not your turn")
                    else:
                        irc.reply( "You are not in the player list" )
                else:
                    irc.reply( "Game is not started" )

            if ( l_sAction=="board" ):
                self.board.display( irc )

            if ( l_sAction=="move" ):
                if (self.game_started):
                    if (msg.nick==self.player.name):
                        if (self.rolled and not self.moved):
                            if (self.double_count == 3):
                                self.player.position.leave( self.player, irc )
                                self.board.jail.enter( self.player, irc )
                            else:
                                can_move = False
                                if (self.player.position.typecase == TC_PRISON):
                                    # try to exit from Jail
                                    # with double
                                    if (self.double_count > 0):
                                        irc.reply( "In Jail - double, exit allowed" )
                                        can_move = True
                                    elif (self.player.jailturn==3):
                                        # 3 turns in jail, must pay for exit
                                        irc.reply( "Pay $50 for exiting" )
                                        self.player.money -= 50
                                        can_move = True
                                    else:
                                        # one more turn in jail
                                        irc.reply( "Must stay in Jail" )
                                        self.players[self.next_player].jailturn += 1
                                else:
                                    can_move = True
                                if (can_move):
                                    self.player.move( self.dice1 + self.dice2, irc )
                                    # if we arrive in jail, then reset double state
                                    if (self.players[self.next_player].position.typecase == TC_PRISON):
                                        self.can_roll_again = False
                            self.moved = True
                        else:
                            irc.reply( "roll the dice or end turn" )
                    else:
                        irc.reply( "not your turn" )
                else:
                    irc.reply( "Game not started" )

            if ( args[0] == "build" ):
                if self.gamestarted( irc ):
                    # @poly build house <group> [prop] : @poly build house 110 1
                    if ( len(args) >= 3 ):
                        if ( args[1]=="house" or arg[1]=="hotel" ):
                            grouptobuild = args[2]
                    if ( len(args) == 4 ):
                        if ( args[1]=="house" or arg[1]=="hotel" ):
                            proptobuild = int( args[3] )


            if ( args[0]=="info" ):
                for player in self.players:
                    if (player.name == msg.nick):
                        player.display_info( irc )

            if ( args[0]=="end" ):
                if (self.game_started):
                    if (msg.nick==self.players[self.next_player].name):
                        if (self.rolled and not self.can_roll_again and self.moved):
                            self.next_player +=1
                            self.next_player %=len(self.players)
                            irc.reply( "%s's turn" % (self.players[self.next_player].name) )
                            self.rolled = False
                            self.can_roll_again = False
                            self.double_count = 0
                        else:
                            irc.reply( "You must roll the dices or move before ending turn" )
                    else:
                        irc.reply( "Not your turn" )
                else:
                    irc.reply("Game not started")

Class = PythonPoly


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
