--------------------------
README pro knihovnu rrslib
--------------------------
Autor: Stanislav Heller, xhelle03@stud.fit.vutbr.cz
Wiki: https://merlin.fit.vutbr.cz/nlp-wiki/index.php/Rrs_library
Posledni uprava tohoto souboru: 11.10.2010 22:19

------------------------+
1. INSTALANCE, SPUSTENI |
------------------------+

Pro spravnou funkci knihovny na serveru athena3 je treba spustit skript:
source ./export_rrslib_path.sh
ktery se nachazi v korenovem adresari knihovny
(/mnt/minerva1/nlp/projects/rrs_library/)

Pro spravny chod knihovny musi byt pouzit pro spusteni Python 2.6
ktery je nainstalovan v rrs_local. Cesta k nemu je ve skriptu
samozrejme exportovana.

Pote uz pokud staci do pythonovskeho skriptu importovat balicek, modul nebo
funkci a pouzivat.

------------------+
2. UKAZKA POUZITI |
------------------+

#!/usr/bin/env python

# import knihovni funkce
from rrslib.web.tools import is_url_alive

# ukazka funkcnosti
print is_url_alive("http://www.google.com")

# melo by vypsat 1


----------------+
3. ARCHITEKTURA |
----------------+
Layout adresare rrs_library:

rrs_library/
	releases/			Ukladani release rrslib
					(bude odstraneno)
	
	rrslib/				Hlavni slozka zdrojaku knihovny
		classifiers/		Klasifikatory
		db/			Objektovy model db, konvertory
		dictionaries/		Slovniky pro extraktory RRS
		extractors/		Extraktory a komponenty
                web/                    Webove nastroje
		others/			Ostatni

	git-repository/			Repositar gitu
		rrslib.git/             Repozitar knihovny
		tests/			Repozitar testu ke knihovne

	qa/				Quality Assurance (knihoven)
		data/			Data pro testovani
		output/			Vysledky testu
		start_test.sh		Spusteni sady testu

	README.txt			Toto readme

	export_rrslib_path.sh		Skript pro export promennych


-------+
4. GIT |
-------+
Wiki o RCS pro rrslib: https://merlin.fit.vutbr.cz/nlp-wiki/index.php/Rrs_library:RCS

Jestlize jste nikdy nepracovali se systemem pro spravu verzi, nezbyva,
nez se podivat na google :).

Pokud jste nikdy nepracovali s gitem, idealni je podivat se do tutorialu
http://ftp.newartisans.com/pub/git.from.bottom.up.pdf
Pokud prechazite ze svn na git nebo chcete jen rychly tutorial, idealni navod
je na fedorahosted https://fedorahosted.org/spacewalk/wiki/GitGuide


4.1. ZACATEK PRACE NA RRSLIB

4.1.1 Nejdrive si zjistete, zda mate nainstalovany git a gitk :)

4.1.2 Klonovani repozitare
      Pro praci z lokalu (remote):
      $ git clone xlogin00@merlin.fit.vutbr.cz/mnt/minerva1/nlp/projects/rrs_library/git-repository/rrslib.git

      Pro praci nekde jine na athene nebo merlinovi:
      $ git clone /mnt/minerva1/nlp/projects/rrs_library/git-repository/rrslib.git

4.2. NASTAVENI
- Nastavte si v configu Vaše jméno a email!
- Commitujte s komentářem tak, aby na prvním řádku (ten se zobrazuje v git log)
  byl důležitý abstrakt změn a na dalších řádcích vyjmenovány přesně změny.
- Před pushnutím vždycky pullněte a mergněte změny!
  (git status; git pull --rebase; gitk -all; git push origin master)
- Pokud se Vám podaří si rozhodit git, rozhodně nepushujte a nebojte se git reset a git revert.


-------------------+
TESTOVANI KNIHOVNY |
-------------------+
Lorem ipsum



