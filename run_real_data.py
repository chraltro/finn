#!/usr/bin/env python3
"""Score real Finn.no listings gathered via web search.

This script uses actual listing data extracted from web search results
to demonstrate the full scoring pipeline with real Finn.no data.
"""

import logging

from alerts.notifier import print_alerts, save_csv, save_results
from main import score_listings
from scraper.finn_search import FinnListing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Real Finn.no listings from web search results
REAL_LISTINGS = [
    # --- Tier 1: Named designer listings ---
    FinnListing(
        finn_kode="385608386",
        title="Arne Jacobsen - Myren stoler i teak",
        price=None,
        description=(
            "4 Arne Jacobsen Myren stoler i teak, modell 3103. Originale designstoler "
            "produsert hos Fritz Hansen. Formspendt teaktre på ben av stål, tidlig modell "
            "med tre ben, i god stand."
        ),
        location="Unknown",
        url="https://www.finn.no/recommerce/forsale/item/385608386",
        search_query="teak stol",
    ),
    FinnListing(
        finn_kode="395285615",
        title="CH23 stol – Hans J. Wegner for Carl Hansen & Søn (NY)",
        price=9000,
        description=(
            "Selger en CH23-stol i oljet eik fra Carl Hansen & Søn, designet av den "
            "ikoniske Hans J. Wegner. Stolen er helt ny. Nypris 11 394 kr."
        ),
        location="Oslo",
        url="https://www.finn.no/recommerce/forsale/item/395285615",
        search_query="wegner stol",
    ),
    FinnListing(
        finn_kode="383367621",
        title="Design stoler av Hans J. Wegner - Butterfly",
        price=28000,
        description=(
            "Selger samlet 2 vakre designstoler fra den verdenskjente Hans J. Wegner. "
            "Stolene er nesten ikke brukt og utrolig vakre! GE460 Butterfly er designet "
            "av Hans J. Wegner. Stolen Butterfly er som en sommerfugl som sitter klar til "
            "å ta av. Stolene selges helst samlet."
        ),
        location="Oslo",
        url="https://www.finn.no/recommerce/forsale/item/383367621",
        search_query="wegner stol",
    ),
    FinnListing(
        finn_kode="388646089",
        title="Wegner GE 290",
        price=30000,
        description=(
            "Merke: Hans J Wegner. Kjøpt for 4-5 år siden hos Utopia. Fremstår som ny."
        ),
        location="Oslo",
        url="https://www.finn.no/recommerce/forsale/item/388646089",
        search_query="wegner stol",
    ),
    FinnListing(
        finn_kode="373045106",
        title="Dansk design stoler. Fritz Hansen",
        price=None,
        description=(
            "Arne Jacobsen 'Syveren/3107' Fritz Hansen — 4 stk heltrukne stoler i lyst "
            "brunt lær. En sand klassiker som er designet af Arne Jacobsen. I god stand, "
            "nesten som ny."
        ),
        location="Unknown",
        url="https://www.finn.no/recommerce/forsale/item/373045106",
        search_query="dansk design stol",
    ),
    FinnListing(
        finn_kode="374332460",
        title="Dansk designstol av Arne Wahl Iversen",
        price=7500,
        description=(
            "Designet av Arne Wahl Iversen med ulltrekk fra Gudbrandsdalen Tekstil. "
            "Modellen heter '247' og er produsert av den danske møbelfabrikken Falster."
        ),
        location="Unknown",
        url="https://www.finn.no/recommerce/forsale/item/374332460",
        search_query="dansk design stol",
    ),
    FinnListing(
        finn_kode="371395199",
        title="Wegner CH88 stol",
        price=None,
        description=(
            "CH88 fra Carl Hansen & Søn er en vakker og funksjonell stol. Det er tydelig "
            "at det er Hans J. Wegner som har gitt form til stolen. Jubileumsutgave med "
            "ben i rødlakkert stål, ryggstøtte og sete i rødlakkert bøk."
        ),
        location="Elverum",
        url="https://www.finn.no/recommerce/forsale/item/371395199",
        search_query="wegner stol",
    ),
    FinnListing(
        finn_kode="180353029",
        title="Nydelig skulpturell stol av Arne Vodder for Sibast møbler",
        price=None,
        description=(
            "Høyrygget, komfortabel og skulpturell stol designet av Arne Vodder på "
            "1960-tallet for Sibast Møbler. Stolen er utført i teak med sete trukket "
            "i et grønt fløyelslignende møbelstoff, med løs pute som enkelt kan skiftes ut."
        ),
        location="Unknown",
        url="https://www.finn.no/bap/webstore/ad.html?finnkode=180353029",
        search_query="Sibast stol",
    ),

    # --- Tier 2: Generic/vague listings (where the real value is) ---
    FinnListing(
        finn_kode="370084060",
        title="Teak stoler fra Vatne Møbelfabrikk",
        price=9500,
        description=(
            "To flotte originale stoler, designet av Rastad & Relling tegnekontor for "
            "Vatne møbelfabrikk. Stoffet er helt, og teak er uten så altfor mange "
            "bruksmerker. Stoffet er av det ettertraktede Unika Væv (Danmark). "
            "Totalt 9 500 kr for begge stolene."
        ),
        location="Porsgrunn",
        url="https://www.finn.no/recommerce/forsale/item/370084060",
        search_query="teak stol",
    ),
    FinnListing(
        finn_kode="397067989",
        title="Retro sofa - teak + to stoler (salong)",
        price=None,
        description=(
            "En solid sofa fra 60/70-tallet med teak ben og armlener. Skumgummi og "
            "ulltrekk ble fornyet i 2015, inkludert to stoler som hører til."
        ),
        location="Bergen",
        url="https://www.finn.no/recommerce/forsale/item/397067989",
        search_query="teak stol",
    ),
    FinnListing(
        finn_kode="416104400",
        title="6 vintage retro spisestuestoler i teak og sort skai",
        price=None,
        description=(
            "Fra 1950-1960-tallet. Klassisk skandinavisk design av høy kvalitet, "
            "med behagelig finish som fremhever de organiske linjene i ryggstøttene."
        ),
        location="Unknown",
        url="https://www.finn.no/recommerce/forsale/item/416104400",
        search_query="teak spisestol",
    ),
    FinnListing(
        finn_kode="395903234",
        title="Vintage teak lenestol fra PI Langlo modell 1871, kan sendes",
        price=None,
        description=(
            "Vintage lenestol fra PI Langlo modell 1871 med originalt møbelstoff i meget "
            "god stand. Pent tidløst stykke skandinavisk design med originalt møbelstoff, "
            "passer godt i et moderne hjem som en statement piece. Sittehøyde 43 cm, "
            "setedybde 45 cm. Kan sendes mot at kjøper betaler frakt 500 kr."
        ),
        location="Unknown",
        url="https://www.finn.no/recommerce/forsale/item/395903234",
        search_query="retro lenestol",
    ),
    FinnListing(
        finn_kode="385824026",
        title="Vintage Pål-lenestol teak med originalt grønt trekk",
        price=None,
        description=(
            "Stilig Retrostol Pål-lenestol i teak med originalt trekk, produsert på "
            "60-tallet, mest sannsynlig ved Liabygda Trevarefabrikk. Stol og trekk er "
            "i meget god vintage stand."
        ),
        location="Unknown",
        url="https://www.finn.no/recommerce/forsale/item/385824026",
        search_query="retro lenestol",
    ),
    FinnListing(
        finn_kode="391462662",
        title="Mid-century Moderne Nordisk Design lenestol",
        price=None,
        description=(
            "A stylish lounge chair with a curved wood frame and black leather seat, "
            "comfortable and elegant. Mid-century modern Nordic design."
        ),
        location="Unknown",
        url="https://www.finn.no/recommerce/forsale/item/391462662",
        search_query="retro lenestol",
    ),
    FinnListing(
        finn_kode="296107582",
        title="Lenestol i teak",
        price=2000,
        description=(
            "Ingmar Relling for Ekornes, Svane Combina selges pga. flytting. "
            "Ingen merker eller slitasje i stoffet. 2000 kr eller høyeste bud. "
            "Må hentes i Elverum."
        ),
        location="Elverum",
        url="https://www.finn.no/recommerce/forsale/item/296107582",
        search_query="retro lenestol",
    ),
    FinnListing(
        finn_kode="440259052",
        title="Nydelig nyrestaurert retro lenestol/saksestol til salgs",
        price=None,
        description=(
            "Retro 60-tallet stol i teak med hvit teddy stoff. Stolen er nyrestaurert, "
            "pusset vekk alt som har vært unødvendig for at treverket skal få et nytt liv."
        ),
        location="Unknown",
        url="https://www.finn.no/recommerce/forsale/item/440259052",
        search_query="teak spisestol",
    ),
    FinnListing(
        finn_kode="392810871",
        title="Loungestol i klassisk dansk design",
        price=4500,
        description=(
            "Loungestoler i klassisk dansk design, utført i formpresset eik med sete "
            "og rygg i svart tekstil, i meget god stand."
        ),
        location="Sarpsborg",
        url="https://www.finn.no/recommerce/forsale/item/392810871",
        search_query="dansk design stol",
    ),
    FinnListing(
        finn_kode="438167133",
        title="Eksklusiv teakskjenk – Brødrene Sørheim – Norsk kvalitet, 60-tallet",
        price=None,
        description=(
            "Stor og sjelden teakskjenk fra Brødrene Sørheim Møbelfabrikk (Nes i Tun), "
            "produsert ca. 1965-1975. Ekte norsk kvalitetsmøbel, kjent for solid håndverk, "
            "vakre materialer og tidløst Scandinavian Modern-design. Tilstanden er svært "
            "god for alderen – nylig renset og behandlet. Utskåret dekorfrise over frontene, "
            "massiv teak på ben og kantlister."
        ),
        location="Kristiansand",
        url="https://www.finn.no/recommerce/forsale/item/438167133",
        search_query="teak skjenk",
    ),
    FinnListing(
        finn_kode="404806411",
        title="Flott retro skap/ skjenk i teak fra 60 tallet. Gratis levering!",
        price=None,
        description=(
            "Norskprodusert retro skap/skjenk i teak, kommode fra 50/60 tallet, "
            "opprinnelig funksjon er stereoskap eller radiokabinett for lp/vinylspiller, "
            "men møbelet fungerer også fint som tv-bord, mini-skjenk, entremøbel etc."
        ),
        location="Unknown",
        url="https://www.finn.no/recommerce/forsale/item/404806411",
        search_query="teak skjenk",
    ),
    FinnListing(
        finn_kode="448530148",
        title="UTSETTES: STORT DØDSBO-SALG",
        price=None,
        description=(
            "Det vil komme egne annonser fortløpende på objekter og ting av høyere "
            "verdi (møbler, tepper, porselen, malerier, etc.) på brukeren sin finn-profil."
        ),
        location="Holmestrand",
        url="https://www.finn.no/recommerce/forsale/item/448530148",
        search_query="dødsbo teak",
    ),
    FinnListing(
        finn_kode="393697390",
        title="Teak entresett fra Talgø møbler, kommode og speil",
        price=1900,
        description=(
            "Nyoppusset flott teak entresett fra Talgø møbler, bestående av teak kommode "
            "med 3 skuffer og sorte ben med gullsko samt et ovalt speil med sort malt "
            "teak-ramme. Selges komplett."
        ),
        location="Askøy",
        url="https://www.finn.no/recommerce/forsale/item/393697390",
        search_query="teak kommode",
    ),
    FinnListing(
        finn_kode="418914874",
        title="Wishbone Y-stol",
        price=4000,
        price_text="4000 kr samlet (1200 pr stol)",
        description=(
            "Selger fire stk pent brukte Hans Wegner Wishbone etterligninger fra "
            "ByKallevig. Selges brukt for 4000.- samlet, eller 1200.- per stol."
        ),
        location="Lillehammer",
        url="https://www.finn.no/recommerce/forsale/item/418914874",
        search_query="wegner stol",
    ),
    FinnListing(
        finn_kode="420915478",
        title="IKEA EKENÄSET Lenestol",
        price=None,
        description=(
            "EKENÄSET lenestol gir rommet et innslag av retrostil inspirert av "
            "skandinavisk design fra 1950-tallet. Klassisk utseende som passer "
            "hvor som helst i hjemmet."
        ),
        location="Unknown",
        url="https://www.finn.no/recommerce/forsale/item/420915478",
        search_query="retro lenestol",
    ),
    FinnListing(
        finn_kode="391746103",
        title="Klassiske danske design stoler H.J Wegner",
        price=None,
        description=(
            "Fire vakre vintage spisestoler i bøk. Stilrent og klassisk dansk design. "
            "Sitteputene har nytt trekk i ull stoff fra Hallingdal."
        ),
        location="Unknown",
        url="https://www.finn.no/recommerce/forsale/item/391746103",
        search_query="wegner stol",
    ),
    FinnListing(
        finn_kode="339404856",
        title="Lenestol Lounge stol dansk design massiv eik",
        price=None,
        description=(
            "En legemliggjøring av nordic living med en internasjonal vri. "
            "Loungestol i massiv eik, dansk design."
        ),
        location="Unknown",
        url="https://www.finn.no/recommerce/forsale/item/339404856",
        search_query="dansk design stol",
    ),
    FinnListing(
        finn_kode="410692454",
        title="Stol i dansk design",
        price=None,
        description=(
            "Vintage stol selges pga plassmangel. Knirker litt. Beliggenhet: Oslo."
        ),
        location="Oslo",
        url="https://www.finn.no/recommerce/forsale/item/410692454",
        search_query="dansk design stol",
    ),
]

if __name__ == "__main__":
    print(f"Scoring {len(REAL_LISTINGS)} real Finn.no listings...\n")

    scored = score_listings(REAL_LISTINGS)

    print_alerts(scored, min_score=10)
    json_path = save_results(scored, filename="real_results.json")
    csv_path = save_csv(scored, filename="real_results.csv")

    # Summary
    high = sum(1 for _, r in scored if r["total_score"] >= 30)
    medium = sum(1 for _, r in scored if 15 <= r["total_score"] < 30)
    low = sum(1 for _, r in scored if r["total_score"] < 15)
    print(f"\nSummary: {len(scored)} listings scored")
    print(f"  High potential (30+): {high}")
    print(f"  Medium potential (15-29): {medium}")
    print(f"  Low potential (<15): {low}")
    print(f"\nAll scored listings (sorted by score):")
    print(f"{'Score':>5} | {'Title':55} | {'Price':>10} | {'URL'}")
    print("-" * 140)
    for listing, result in sorted(scored, key=lambda x: -x[1]["total_score"]):
        price_str = f"{listing.price} kr" if listing.price else "N/A"
        print(
            f"{result['total_score']:>5} | {listing.title[:55]:55} | {price_str:>10} | {listing.url}"
        )
