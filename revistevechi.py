# -*- coding: utf-8 -*-

import sqlite3
from string import Template
import re
import operator
import os
import collections

conn = sqlite3.connect("arhiva_reviste.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

template = Template("""$titlu
$contribuie
| {{ $img_coperta?direct&150 }} ||
^ Info ^^
$nr_pagini$disc_demo$joc_complet$pret$supliment$redactor_sef
$tabel_download
$lista_redactori
$cuprins""")

luna_string = {
    1: "ianuarie",
    2: "februarie",
    3: "martie",
    4: "aprilie",
    5: "mai",
    6: "iunie",
    7: "iulie",
    8: "august",
    9: "septembrie",
    10: "octombrie",
    11: "noiembrie",
    12: "decembrie",
}

# functie folosita pentru a genera textul unei ancore (#ancora)
# de exemplu, pentru numele redactorilor: K'shu -> kshu, Marius Ghinea -> marius_ghinea
def genereaza_ancora(string):
    return re.sub('[^A-z0-9 -]', '', string).lower().replace(" ", "_")

# face ca un string care contine caractere precum "|" si "^" sa poata fi inclus intr-un tabel
def in_tabel(string):
    return string.replace("|", "%%|%%").replace("^", "%%^%%")

# transofrma un cursor.fetchall() intr-o lista de dict-uri
def dictfetchall(cursor):
    return [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

# functie care ia din DB link-urile de download si le sorteaza dupa prioritate
def get_downloads(editie_id, categorie):
    download_prioritati = ("archive.org", "libgen", "scribd.com", "mediafire.com", "mega.nz")

    c.execute("SELECT item, link FROM downloads WHERE editie_id = ? AND categorie = ?;", (str(editie_id), categorie))
    downloads = dictfetchall(c)

    for dwd in downloads:
        dwd["nume"] = dwd["link"].split("//", 1)[-1].split("/", 1)[0].replace("www.", "", 1)
        if dwd["nume"] in download_prioritati:
            dwd["prioritate"] = download_prioritati.index(dwd["nume"])
        else:
            dwd["prioritate"] = 99
    return sorted(downloads, key=operator.itemgetter("prioritate"))


toate_revistele = conn.cursor().execute("SELECT * FROM editii WHERE revista_id = 7 ORDER BY an;")

for e in toate_revistele:

    # sari peste revistele care nu au numar
    if e["numar"] == "":
        continue

    # creeaza directoare
    os.makedirs("pages/level/%d" % e["an"], exist_ok=True)
    linkpath = ":level:%d:%d" % (e["an"], e["luna"])
    if e["tip"] == "supliment":
        linkpath = "%s-supliment" % linkpath
        os.makedirs("media/level/%d/%d-supliment" % (e["an"], e["luna"]), exist_ok=True)
    else:
        os.makedirs("media/level/%d/%d" % (e["an"], e["luna"]), exist_ok=True)


    titlu = "====== LEVEL nr. %s (%s %s) ======" % (e["numar"], luna_string[e["luna"]], e["an"])
    if e["tip"] == "supliment":
        titlu = "====== Supliment LEVEL mobile (%s %s) ======" % (luna_string[e["luna"]], e["an"])

    contribuie = ""
    if e["scan_info_pg_lipsa"]:
        contribuie = "\n<color red>--- //%s %s. Vă rugăm să [[:contribuie|contribuiți]].// ---</color>\n"
        # dacă scan_info_pg_lipsa conține caracterul "," sau "-", atunci lipsesc mai multe pagini
        if ',' in e["scan_info_pg_lipsa"] or '-' in e["scan_info_pg_lipsa"]:
            contribuie = contribuie % ("Lipsesc paginile", e["scan_info_pg_lipsa"])
        else:
            contribuie = contribuie % ("Lipsește pagina", e["scan_info_pg_lipsa"])


    ### tabel info ###

    img_coperta = "%s:coperta.jpg" % linkpath

    nr_pagini = ""
    if e["nr_pagini"] not in (None, ""):
        nr_pagini = "\n| **Pagini** | %d |" % e["nr_pagini"]

    disc_demo = ""
    if e["disc_demo"] not in (None, ""):
        if "CD" in e["disc_demo"]:
            img_disc = "%s:cd.jpg" % linkpath
        elif "DVD" in e["disc_demo"]:
            img_disc = "%s:dvd.jpg" % linkpath
        else:
            print("tip de disc nou: %s" % e["disc_demo"])
            quit()
        disc_demo = "\n| **Disc demo** | " + e["disc_demo"] + " {{" + img_disc + "?direct&20}}|" # TODO: daca sunt mai multe discuri?

    joc_complet = ""
    if e["joc_complet"] not in (None, ""):
        joc_complet = "\n| **Joc complet** | " + e["joc_complet"] + " |"

    pret = ""
    if e["pret"] not in (None, ""):
        pret = "\n| **Preț** | " + str(e["pret"]) + " lei|"

    redactor_sef = ""
    if e["redactor_sef"] not in (None, ""):
        redactor_sef = "[[level:redactori#" + genereaza_ancora(e["redactor_sef"]) + "|" + e["redactor_sef"] + "]]"
        redactor_sef = "\n| **Redactor-șef** | " + redactor_sef + " |"

    supliment = ""
    if e["tip"] == "supliment":
        supliment = "\n| **Revista-mamă** | [[:level:%d:%d|LEVEL (%s %d)]] |" % (e["an"], e["luna"], luna_string[e["luna"]], e["an"])
    else:
        c.execute("SELECT * FROM editii WHERE tip='supliment' AND parinte_editie_id = ?;", (e["editie_id"], ))
        supl = c.fetchone()
        if supl:
            supliment = "\n| **Supliment** | [[" + linkpath + "-supliment|LEVEL mobile]] |"

    ### download revista ###

    tabel_download = ""
    link_pagina_cuprins = ""

    downloads_revista = get_downloads(e["editie_id"], "revista")

    if len(downloads_revista):
        # extrage link-ul pentru cuprins
        link_cuprins = downloads_revista[0]["link"]
        if "archive.org" in link_cuprins:
            id_revista = link_cuprins.rsplit('/', 1)[-1]
            link_pagina_cuprins = "[[https://archive.org/stream/" + id_revista + "#page/n%d/mode/2up|%s]]"
        # construieste tabelul
        for dwd in downloads_revista:
            tabel_download += "| ::: |[[%s|%s]]|\n" % (dwd["link"], dwd["nume"])
        tabel_download = tabel_download.replace(":::", "**Revista**", 1)


    ### download CD/DVD ###

    link_cuprins_disc_demo = ""
    c.execute("SELECT pg_toc FROM articole WHERE editie_id = ? AND rubrica = 'Cuprins CD/DVD';", (e["editie_id"], ))
    pagina = c.fetchone()
    if pagina:
        pagina = pagina["pg_toc"]
        if link_pagina_cuprins != "":
            link_cuprins_disc_demo = link_pagina_cuprins % (pagina - 1, "cuprins") + ", "

    downloads_CD = get_downloads(e["editie_id"], "CD")

    if len(downloads_CD):
        tabel_download += "| **CD** |{{%s?linkonly|scan}}, %s[[catalog]]|\n" % (img_disc, link_cuprins_disc_demo)
        for dwd in downloads_CD:
            tabel_download += "| ::: |[[%s|imagine completă (%s)]]|\n" % (dwd["link"], dwd["nume"])

    downloads_DVD = get_downloads(e["editie_id"], "DVD")
    if len(downloads_DVD):
        tabel_download += "| **DVD** |{{%s?linkonly|scan}}, %s[[catalog]]|\n" % (img_disc, link_cuprins_disc_demo)
        for dwd in downloads_DVD:
            tabel_download += "| ::: |[[%s|imagine completă (%s)]]|\n" % (dwd["link"], dwd["nume"])

    if tabel_download != "":
        tabel_download = "^ Download ^^\n" + tabel_download


    ### lista redactori ###

    lista_redactori = ""
    redactori = {}
    for r in c.execute("SELECT autor, count() nr_articole FROM articole WHERE editie_id = ? GROUP BY autor;", (e["editie_id"], )):
        if not r["autor"]:
            continue
        # autorii pot fi mai multi, separati de virgule
        autori = r["autor"].split(",")
        for autor in autori:
            autor = autor.strip() # sterge spatiile de la inceput si sfarsit
            if autor not in redactori:
                redactori[autor] = 0
            redactori[autor] += r["nr_articole"]
    redactori = collections.OrderedDict(sorted(redactori.items())) # sorteaza redactorii alfabetic
    for autor, nr_articole in redactori.items():
        ancora = genereaza_ancora(autor)
        articol_e = "articole" if nr_articole > 1 else "articol"
        lista_redactori += "\n  * [[level:redactori#%s|%s]] (%s %s)" % (ancora, autor, nr_articole, articol_e)
    if lista_redactori != "":
        lista_redactori = "\n===== Redactori =====\n" + lista_redactori + "\n"


    ### cuprins ###

    cuprins = ""
    rubrica = ""
    for cup in c.execute("SELECT * FROM articole WHERE editie_id = ? ORDER BY pg_toc;", (e["editie_id"], )):

        if cup["rubrica"] in ("Cuprins CD/DVD", "Cuprins"):
            continue

        if rubrica != cup["rubrica"]:
            rubrica = cup["rubrica"]
            cuprins += "^" + in_tabel(rubrica) + "^^^^\n"

        titlu = cup["titlu"] if cup["titlu"] != "" else rubrica

        pagina = cup["pg_toc"]
        # daca link_pagina_cuprins a fost definit, completeaza-l si foloseste-l in loc de pagina
        if link_pagina_cuprins != "":
            pagina = link_pagina_cuprins % (pagina - 1, pagina)

        cuprins += Template("|$pagina|$titlu|$autor|$nota|\n").substitute(
            pagina = pagina,
            titlu = in_tabel(titlu),
            autor = cup["autor"],
            nota = in_tabel(cup["nota"]),
        )
    if cuprins != "":
        cuprins = "\n===== Cuprins =====\n" + cuprins + "\n"
    else:
        contribuie += "\n<color red>--- //Cuprinsul lipsește. Vă rugăm să [[:contribuie|contribuiți]].// ---</color>\n"


    ### output pagina wiki ###

    if e["tip"] == "supliment":
        fo = open("pages/level/%d/%d-supliment.txt" % (e["an"], e["luna"]), "w")
    else:
        fo = open("pages/level/%d/%d.txt" % (e["an"], e["luna"]), "w")

    fo.write(template.substitute(
        titlu = titlu,
        contribuie = contribuie,
        img_coperta = img_coperta,
        disc_demo = disc_demo,
        nr_pagini = nr_pagini,
        joc_complet = joc_complet,
        pret = pret,
        supliment = supliment,
        redactor_sef = redactor_sef,
        tabel_download = tabel_download,
        lista_redactori = lista_redactori,
        cuprins = cuprins,
    ))
    fo.close()


### pagina principala ###

pagina_principala = """https://revistevechi.blogspot.ro/2011/07/level-1997-2004-colectia-de-reviste.html

reviste: https://mega.nz/#F!SxckBRQa!AZl0AUzjFQvg0AED2iWDBA

CD/DVD 1997-2002: https://mega.nz/#F!b8kwFCgQ!i0kDgPnXr0YWJPYW3BdFgA

CD/DVD 2003-2006: https://mega.co.nz/#F!m5MG3C5Z!8CP3x3rnrJ_IHiTJN3FVuA

Cea mai longevivă revistă de jocuri din România.
  * https://en.wikipedia.org/wiki/LeveL#LEVEL_in_Romania
  * https://ro.wikipedia.org/wiki/Level
  * http://nivelul2.ro/

[[level:Redactori]]

"""

ani = conn.cursor().execute("SELECT DISTINCT an FROM editii WHERE tip = 'revista' AND revista_id = 7 ORDER BY an;")

for an in ani:

    an = an["an"]

    template_an = "\n\n===== %d =====\n\n" % an
    if (an != 1997):
        template_an += "^Ian^Feb^Mar^Apr^Mai^Iun^\n"
        template_an += "|$l1|$l2|$l3|$l4|$l5|$l6|\n"
    template_an += "^Iul^Aug^Sep^Oct^Nov^Dec^\n"
    template_an += "|$l7|$l8|$l9|$l10|$l11|$l12|\n"

    luni_reviste = []
    for rand in c.execute("SELECT DISTINCT luna FROM editii WHERE tip = 'revista' AND revista_id = 7 AND an = ? ORDER BY luna;", (an, )):
        luni_reviste.append(rand["luna"])

    l = {}
    for luna in range(1, 13):
        if luna in luni_reviste: # daca exista revista
            l[luna] = "[[level:%(an)d:%(luna)d|{{:level:%(an)d:%(luna)d:coperta.jpg?nolink&0x144}}]]" % {"an": an, "luna": luna}
        else: # daca nu exista revista
            l[luna] = "{{coperta_default.png?nolink&0x144}}"

    pagina_principala += Template(template_an).substitute(
        l1 = l[1], l2 = l[2], l3 = l[3], l4 = l[4], l5 = l[5], l6 = l[6],
        l7 = l[7], l8 = l[8], l9 = l[9], l10 = l[10], l11 = l[11], l12 = l[12],
    )

fo = open("pages/level.txt", "w")
fo.write(pagina_principala)
fo.close()
