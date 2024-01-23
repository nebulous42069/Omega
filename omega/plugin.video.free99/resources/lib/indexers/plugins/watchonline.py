# -*- coding: utf-8 -*-

import re
import requests

from resources.lib.indexers import navigator

from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import control
from resources.lib.modules import sources
from resources.lib.modules import source_utils
from resources.lib.modules import scrape_sources
#from resources.lib.modules import log_utils

control.moderator()


site_list = [
    {'title': '3rd Rock From The Sun', 'url': 'https://watch3rdrockfromthesunonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/V9dspjr/3rd-Rock-From-the-Sun-min.jpg'},
    {'title': '30 Rock', 'url': 'https://watch30rockonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/T40BFpW/30-rock-min.jpg'},
    {'title': 'According To Jim', 'url': 'https://watchaccordingtojimonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/X3DQqH0/According-to-Jim-min.jpg'},
    {'title': 'American Dad', 'url': 'https://iwatchamericandadonline.com', 'endings': ['/series/american-dad/'], 'image': 'https://i.ibb.co/Hn1hG1c/American-Dad-min.jpg'},
    {'title': 'Archer', 'url': 'https://watcharcheronline.cc', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/HCZpHxf/archer-min.jpg'},
    {'title': 'Arrested Development', 'url': 'https://iwatcharresteddevelopment.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/fGVQ7WM/Arrested-Development-min.jpg'},
    {'title': 'Arrow', 'url': 'https://watcharrowonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/khwrLqv/Arrow-min.jpg'},
    {'title': 'Bates Motel', 'url': 'https://watchbatesmotelonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/bF65y8W/batesmotel-min.jpg'},
    {'title': 'Baywatch', 'url': 'https://watchbaywatchonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/JddKSpD/baywatch-min.jpg'},
    {'title': 'Bojack Horseman', 'url': 'https://watchbojackhorseman.online', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/zSKGYts/bojack-horseman-min.jpg'},
    {'title': 'Bones', 'url': 'https://watchbonesonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/hZ9N4nn/bones-min.jpg'},
    {'title': 'Breaking Bad', 'url': 'https://watchbreakingbad.com', 'endings': ['/movies/', '/seasons/'], 'image': 'https://i.ibb.co/bgySpfh/Breaking-Bad-min.jpg'},
    {'title': 'Brooklyn Nine-Nine', 'url': 'https://watchbrooklynnine-nine.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/SfGPrqy/Brooklyn-Nine-Nine-min.jpg'},
    {'title': 'Californication', 'url': 'https://watchcalifornicationonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/ZMkwYyG/californication-min.jpg'},
    {'title': 'Castle', 'url': 'https://watchcastleonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/yQjydbb/castle-min.jpg'},
    {'title': 'Charmed', 'url': 'https://watchcharmedonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/VLHH9d2/charmed-min.jpg'},
    {'title': 'Cheers', 'url': 'https://watchcheersonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/0JjC4v6/cheers-min.jpg'},
    {'title': 'Chuck (Broken?)', 'url': 'https://watchchuckonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/34cGL8L/Chuck-min.jpg'},
    {'title': 'Community', 'url': 'https://iwatchcommunityonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/tMMkKf9/Comnity-min.jpg'},
    {'title': 'Criminal Minds', 'url': 'https://watchcriminalminds.com', 'endings': ['/series/criminal-minds/'], 'image': 'https://i.ibb.co/GQWXm8f/Criminal-Minds-min.jpg'},
    {'title': 'Curb Your Enthusiasm', 'url': 'https://watchcurbyourenthusiasm.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/KrW5tYq/curb-your-enthusiasm-min.jpg'},
    {'title': 'Desperate Housewives', 'url': 'https://iwatchdesperatehousewives.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/Sxygn4q/desperate-housewives-min.jpg'},
    {'title': 'Doctor Who', 'url': 'https://watchdoctorwhoonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/HBK5c4h/doctor-who-min.jpg'},
    {'title': 'Downton Abbey', 'url': 'https://watchdowntonabbeyonline.com', 'endings': ['/season-watch/', '/christmas-specials/'], 'image': 'https://i.ibb.co/WxHS2ht/downton-abbey-min.jpg'},
    {'title': 'Elementary', 'url': 'https://watchelementaryonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/yXnfnTf/elementary-min.jpg'},
    {'title': 'ER', 'url': 'https://watcheronline.net', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/mGy2jLt/er-min.jpg'},
    {'title': 'Everybody Loves Raymond', 'url': 'https://watcheverybodylovesraymond.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/hs7NQ3L/everybody-loves-raymond-min.jpg'},
    {'title': 'Family Guy', 'url': 'https://watchfamilyguyonline.com', 'endings': ['/series/family-guy/'], 'image': 'https://i.ibb.co/P1SMng6/Famy-Guy-min.jpg'},
    {'title': 'Friends (Broken?)', 'url': 'https://iwatchfriendsonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/sVwMSQK/Friends-min.jpg'},
    {'title': 'Fugget About It', 'url': 'https://watchfuggetaboutit.online', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/frkNwph/fugget-about-it-min.jpg'},
    {'title': 'Futurama', 'url': 'https://watchfuturamaonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/h9Lh8km/Futurama-min.jpg'},
    {'title': 'Game Of Thrones', 'url': 'https://iwatchgameofthrones.cc', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/dWNF4mY/Game-of-Thrones-min.jpg'},
    {'title': 'Gilmore Girls', 'url': 'https://watchgilmoregirlsonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/fXNVyF5/gmores-min.jpg'},
    {'title': 'Glee (Broken?)', 'url': 'https://watchgleeonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/gzqn1hs/glee-min.jpg'},
    {'title': 'Gossip Girl', 'url': 'https://watchgossipgirlonline.net', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/2Y3TSG1/gossip-girl-min.jpg'},
    {'title': 'Greek', 'url': 'https://watchgreekonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/Kxc7728/eek-min.jpg'},
    {'title': 'Greys Anatomy', 'url': 'https://watchgreysanatomy.com', 'endings': ['/series/greys-anatomy/'], 'image': 'https://i.ibb.co/fQqSfdr/greysanatomy-min.jpg'},
    {'title': 'Hawaii Five-0', 'url': 'https://watchhawaiifive0online.com', 'endings': ['/series/hawaii-five-0/'], 'image': 'https://i.ibb.co/J5hV6LV/hawaii-five-0-min.jpg'},
    {'title': 'Heroes', 'url': 'https://watchheroes.online', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/CQDZ0fj/heroes-min.jpg'},
    {'title': 'Hogans Heroes', 'url': 'https://watchhogansheroes.online', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/T12fhYR/hogan-s-heroes-min.jpg'},
    {'title': 'House Of Cards (Broken?)', 'url': 'https://watchhouseofcard_news.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/ZG8wg9h/House-of-Cards-min.jpg'},
    {'title': 'House', 'url': 'https://watchhouseonline.net', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/WcQMLK5/house-min.jpg'},
    {'title': 'How I Met Your Mother', 'url': 'https://watchhowimetyourmother.online', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/6wZcwyF/how-i-met-your-mother-min.jpg'},
    {'title': 'Impractical Jokers', 'url': 'https://watchimpracticaljokers.online', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/8mTMJ0W/impractical-jokers-min.jpg'},
    {'title': 'Its Always Sunny In Philadelphia', 'url': 'https://iwatchitsalwayssunnyinphiladelphia.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/8PtcJCp/It-s-Always-Sunny-in-Phadelphia-min.jpg'},
    {'title': 'Lost', 'url': 'https://watchlostonline.net', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/H71yNtb/lost-min.jpg'},
    {'title': 'Louie', 'url': 'https://watchlouieonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/phHc3k2/Louie-min.jpg'},
    {'title': 'Mad Men (Broken?)', 'url': 'https://watchmadmenonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/TTc2B2k/mad-men-min.jpg'},
    {'title': 'Malcolm In The Middle (Broken?)', 'url': 'https://watchmalcolminthemiddle.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/S07hWLt/malcolm-in-the-middle-min.jpg'},
    {'title': 'Mash', 'url': 'https://watchmash.online', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/THZKMHm/mash-min.jpg'},
    {'title': 'Modern Family', 'url': 'https://watchmodernfamilyonline.com', 'endings': ['/series/modern-family/'], 'image': 'https://i.ibb.co/MD9kwxk/Modern-Famy-min.jpg'},
    {'title': 'Monk (Broken?)', 'url': 'https://watchmonkonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/TMtCncc/monk-min.jpg'},
    {'title': 'My Name Is Earl', 'url': 'https://watchmynameisearl.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/nPC7VJ9/my-name-is-earl-min.jpg'},
    {'title': 'MythBusters', 'url': 'https://watchmythbustersonline.cc', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/1J9vvfP/mythbusters-536a978e2a5ab-min.jpg'},
    {'title': 'New Girl', 'url': 'https://watchnewgirlonline.net', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/sRJ4qy9/new-girl-min.jpg'},
    {'title': 'Once Upon A Time', 'url': 'https://watchonceuponatimeonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/SQ9mr3f/once-upon-a-time-min.jpg'},
    {'title': 'One Tree Hill', 'url': 'https://watchonetreehillonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/qYYjkLy/one-tree-hill-min.jpg'},
    {'title': 'Only Fools And Horses', 'url': 'https://watchonlyfoolsandhorses.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/HGRbL24/only-fools-and-horses-min.jpg'},
    {'title': 'Orange Is The New Black', 'url': 'https://watchorangeisthenewblack.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/1Z49VtH/Orange-Is-the-New-Black-min.jpg'},
    {'title': 'OZ', 'url': 'https://watchozonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/j6m2KpR/OZ-min.jpg'},
    {'title': 'Parks And Recreation', 'url': 'https://watchparksandrecreation.net', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/FKxJtTg/parks-and-recreation-min.jpg'},
    {'title': 'Pretty Little Liars', 'url': 'https://watchprettylittleliarsonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/zJtfWs4/pretty-little-liars-min.jpg'},
    {'title': 'Psych', 'url': 'https://watchpsychonline.net', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/njr4Hh1/psych-min.jpg'},
    {'title': 'Regular Show (Broken?)', 'url': 'https://watchregularshowonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/CHzphD8/Regular-Show-min.jpg'},
    {'title': 'Roseanne', 'url': 'https://watchroseanneonline.com', 'endings': ['/series/roseanne/'], 'image': 'https://i.ibb.co/1rPm8Mb/roseanne-min.jpg'},
    {'title': 'Rules Of Engagement', 'url': 'https://watchrulesofengagementonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/qNXDTyT/rules-of-engagement-min.jpg'},
    {'title': 'Scandal', 'url': 'https://watchscandalonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/VDTyzSs/scandal-2012-5b13cd946ab1d-min.jpg'},
    {'title': 'Scrubs', 'url': 'https://watchscrubsonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/3fb8VDx/scrubs-min.jpg'},
    {'title': 'Seinfeld', 'url': 'https://watchseinfeld.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/vQSg2zt/seinfeld-min.jpg'},
    {'title': 'Sex And The City', 'url': 'https://watchsexandthecity.com', 'endings': ['/movies/', '/season-watch/'], 'image': 'https://i.ibb.co/FWsd69v/sex-and-the-city-min.jpg'},
    {'title': 'Skins', 'url': 'https://watchskinsonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/7jFwJHr/skins-5c3e924337e14-min.jpg'},
    {'title': 'Smallville (Broken?)', 'url': 'https://watchsmallvilleonline.net', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/qF7FHKS/smallville-min.jpg'},
    {'title': 'South Park', 'url': 'https://watchsouthpark.tv', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/ypBPhzF/south-park-min.jpg'},
    {'title': 'SpongeBob SquarePants', 'url': 'https://watchspongebobsquarepantsonline.com', 'endings': ['/series/spongebob-squarepants/'], 'image': 'https://i.ibb.co/7bWjRXK/spongebob-1-min.jpg'},
    {'title': 'Suits', 'url': 'https://watchsuitsonline.net', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/z7x8hy8/suits-min.jpg'},
    {'title': 'Teen Wolf', 'url': 'https://watchteenwolfonline.net', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/Vm6YCM8/teen-wolf-min.jpg'},
    {'title': 'That 70s Show', 'url': 'https://watchthat70show.net', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/9pmNDg7/that-70s-show-53548fb0b06fe-min.jpg'},
    {'title': 'The 100', 'url': 'https://watchthe100online.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/9TcrCpZ/the100-min.jpg'},
    {'title': 'The Big Bang Theory', 'url': 'https://watchthebigbangtheory.net', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/0XMCxxc/the-big-bang-theory-55166a0905085-min.jpg'},
    {'title': 'The Flintstones', 'url': 'https://watchtheflintstones.online', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/qNqY7bH/the-flintstones-min.jpg'},
    {'title': 'The Fresh Prince Of Bel-Air', 'url': 'https://watchthefreshprinceofbel-air.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/vJ2WjQ1/the-fresh-prince-of-bel-air-min.jpg'},
    {'title': 'The King Of Queens', 'url': 'https://watchthekingofqueens.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/sgFmHXd/the-king-of-queens-min.jpg'},
    {'title': 'The Mentalist (Broken?)', 'url': 'https://watchthementalistonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/mFVFtgL/the-mentalist-min.jpg'},
    {'title': 'The Middle', 'url': 'https://watchthemiddleonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/yXjRQKQ/the-middle-min.jpg'},
    {'title': 'The Office', 'url': 'https://watchtheofficetv.com', 'endings': ['/hd-season-link/'], 'image': 'https://i.ibb.co/wgfcBxG/the-office-min.jpg'},
    {'title': 'The Ricky Gervais Show', 'url': 'https://watchtherickygervaisshow.online', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/PwGs2jW/the-ricky-gervais-show-min.jpg'},
    {'title': 'The Vampire Diaries', 'url': 'https://watchthevampirediaries.net', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/yRf1Tns/the-vampire-diaries-min.jpg'},
    {'title': 'The Walking Dead', 'url': 'https://iwatchthewalkingdead.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/Wyj9gr4/the-walking-dead-543f7e49970ed-min.jpg'},
    {'title': 'The West Wing', 'url': 'https://watchthewestwing.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/FzpQVsH/the-west-wing-5fd6f5e0b2f8e-min.jpg'},
    {'title': 'Two And A Half Men', 'url': 'https://watchtwoandahalfmenonline.com', 'endings': ['/season-watch/'], 'image': 'https://i.ibb.co/0ttYFGN/two-and-a-half-men-min.jpg'},
    {'title': 'Weeds', 'url': 'https://watchweedsonline.com', 'endings': ['/seasons/'], 'image': 'https://i.ibb.co/d0r3yqj/weeds-min.jpg'}
]


odd_domains = [
    'iwatchamericandadonline.com', 'watchcriminalminds.com', 'watchfamilyguyonline.com', 'watchgreysanatomy.com', 
    'watchhawaiifive0online.com', 'watchmodernfamilyonline.com', 'watchroseanneonline.com', 'watchspongebobsquarepantsonline.com'
]


class Indexer:
    def __init__(self):
        self.ajax_link = '/wp-admin/admin-ajax.php'
        self.hostDict = sources.sources().getHostDict()
        self.session = requests.Session()
        self.list = []


    def root(self):
        try:
            for site in site_list:
                title = client_utils.replaceHTMLCodes(site['title'])
                url = site['url']
                image = site['image']
                endings = site['endings']
                link = url + '$$$' + '^^^'.join([i for i in endings])
                self.list.append({'title': title, 'url': link, 'image': image, 'action': 'watchonline_scrape_seasons'})
            navigator.navigator().addDirectory(self.list)
            return self.list
        except:
            #log_utils.log('root', 1)
            return self.list


    def scrape_seasons(self, url):
        try:
            base_link = url.split('$$$')[0]
            self.list.append({'title': 'Random Episode (Sometimes Fails)', 'url': base_link+'/?redirect_to', 'image': None, 'action': 'watchonline_scrape_episode'})
            ends = url.split('$$$')[1].rsplit('^^^')
            for end in ends:
                site_link = base_link + end
                site_html = client.scrapePage(site_link, timeout='30').text
                if '<div class="pagination">' in site_html:
                    pagination = client_utils.parseDOM(site_html, 'div', attrs={'class': 'pagination'})[0]
                    page2_link = client_utils.parseDOM(pagination, 'a', ret='href')[0]
                    site_html += client.scrapePage(page2_link, timeout='30').text
                if '/series/' in site_link:
                    image = client_utils.parseDOM(site_html, 'img', ret='src')[0]
                    seasons = client_utils.parseDOM(site_html, 'li', attrs={'id': r'menu-item-.*?'})
                    for i in seasons:
                        try:
                            title = client_utils.parseDOM(i, 'a')[0]
                            title = client_utils.replaceHTMLCodes(title)
                            if title == 'Home' or title == 'TV Shows' or title == 'Seasons' or title == 'Season List' or title == 'Other' or title == 'Other Websites':
                                continue
                            link = client_utils.parseDOM(i, 'a', ret='href')[0]
                            if not base_link in link:
                                link = base_link + link
                            self.list.append({'title': title, 'url': link, 'image': image, 'action': 'watchonline_scrape_episodes'})
                        except:
                            pass
                else:
                    seasons = client_utils.parseDOM(site_html, 'article')
                    for i in seasons:
                        try:
                            title = client_utils.parseDOM(i, 'img', ret='alt')[0]
                            title = client_utils.replaceHTMLCodes(title)
                            link = client_utils.parseDOM(i, 'a', ret='href')[0]
                            if not base_link in link:
                                link = base_link + link
                            image = client_utils.parseDOM(i, 'img', ret='src')[0]
                            self.list.append({'title': title, 'url': link, 'image': image, 'action': 'watchonline_scrape_episodes'})
                        except:
                            pass
            navigator.navigator().addDirectory(self.list)
            return self.list
        except:
            #log_utils.log('scrape_seasons', 1)
            return self.list


    def scrape_episodes(self, url):
        try:
            base_host = source_utils.get_host(url)
            base_link = 'https://' + base_host
            html = client.scrapePage(url, timeout='30').text
            if any(i in url for i in odd_domains):
                episodes = client_utils.parseDOM(html, 'article')
                for i in episodes:
                    try:
                        title = client_utils.parseDOM(i, 'h2', attrs={'class': 'entry-title'})[0]
                        title = client_utils.replaceHTMLCodes(title)
                        link = client_utils.parseDOM(i, 'a', ret='href')[0]
                        if not base_link in link:
                            link = base_link + link
                        image = client_utils.parseDOM(i, 'img', ret='src')[0]
                        if image.startswith('//'):
                            image = 'https:' + image
                        self.list.append({'title': title, 'url': link, 'image': image, 'action': 'watchonline_scrape_episode'})
                    except:
                        pass
            else:
                episodes = client_utils.parseDOM(html, 'li', attrs={'class': r'mark-.*?'})
                for i in episodes:
                    try:
                        title1 = client_utils.parseDOM(i, 'div', attrs={'class': 'numerando'})[0]
                        title2 = client_utils.parseDOM(i, 'div', attrs={'class': 'episodiotitle'})[0]
                        title2 = client_utils.parseDOM(title2, 'a')[0]
                        title_layout = '[B]%s[/B] (%s)' % (title1, title2)
                        title = client_utils.replaceHTMLCodes(title_layout)
                        link = client_utils.parseDOM(i, 'a', ret='href')[0]
                        if not base_link in link:
                            link = base_link + link
                        image = client_utils.parseDOM(i, 'img', ret='src')[0]
                        self.list.append({'title': title, 'url': link, 'image': image, 'action': 'watchonline_scrape_episode'})
                    except:
                        pass
            navigator.navigator().addDirectory(self.list)
            return self.list
        except:
            #log_utils.log('scrape_episodes', 1)
            return self.list


    def scrape_episode(self, url):
        try:
            base_host = source_utils.get_host(url)
            base_link = 'https://' + base_host
            if '/?redirect_to' in url:
                url += '=random&post_type=episodes'
            html = client.scrapePage(url, timeout='30').text
            if any(i in url for i in odd_domains):
                results = client_utils.parseDOM(html, 'iframe', ret='data-src')
                for result in results:
                    try:
                        result_url = client_utils.replaceHTMLCodes(result)
                        result_html = client.scrapePage(result_url, timeout='30').text
                        result_link = client_utils.parseDOM(result_html, 'iframe', ret='src')[0]
                        for source in scrape_sources.process(self.hostDict, result_link):
                            title = '%s ( %s %s)' % (source['source'], source['quality'], source['info'])
                            link = source['url']
                            self.list.append({'title': title, 'url': link, 'image': None, 'action': 'alt_play'})
                    except:
                        #log_utils.log('scrape_episode', 1)
                        pass
            else:
                customheaders = {
                    'Host': base_host,
                    'Accept': '*/*',
                    'Origin': base_link,
                    'X-Requested-With': 'XMLHttpRequest',
                    'User-Agent': client.UserAgent,
                    'Referer': url,
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
                post_link = base_link + self.ajax_link
                results = re.compile('''class=['"]dooplay_player_option['"] data-type=['"](.+?)['"] data-post=['"](.+?)['"] data-nume=['"](\d+)['"]>''', re.DOTALL).findall(html)
                for data_type, data_post, data_nume in results:
                    try:
                        payload = {'action': 'doo_player_ajax', 'post': data_post, 'nume': data_nume, 'type': data_type}
                        r = self.session.post(post_link, headers=customheaders, data=payload)
                        i = r.text
                        p = i.replace('\\', '')
                        link = client_utils.parseDOM(p, 'iframe', ret='src')[0]
                        for source in scrape_sources.process(self.hostDict, link):
                            title = '%s ( %s %s)' % (source['source'], source['quality'], source['info'])
                            link = source['url']
                            self.list.append({'title': title, 'url': link, 'image': None, 'action': 'alt_play'})
                    except:
                        #log_utils.log('scrape_episode', 1)
                        pass
            navigator.navigator().addDirectory(self.list)
            return self.list
        except:
            #log_utils.log('scrape_episode', 1)
            control.infoDialog('Error : No Stream Available.', sound=False, icon='INFO')
            return self.list


