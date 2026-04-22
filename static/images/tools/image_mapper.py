import pandas as pd

df = pd.read_csv("data/watches.csv")

def img(row):
    name = str(row["name"]).lower()
    brand = str(row["brand"]).lower()

    # Rolex
    if brand == "rolex":
        if "submariner" in name:
            return "/static/images/watches/rolex_submariner.png"
        elif "gmt" in name or "batman" in name or "pepsi" in name or "root beer" in name:
            return "/static/images/watches/rolex_gmt.png"
        elif "daytona" in name or "cosmograph" in name:
            return "/static/images/watches/rolex_daytona.png"
        elif "day-date" in name:
            return "/static/images/watches/rolex_daydate.png"
        elif "datejust" in name:
            return "/static/images/watches/rolex_datejust.png"
        elif "sky-dweller" in name:
            return "/static/images/watches/rolex_skydweller.png"
        elif "yacht-master" in name:
            return "/static/images/watches/rolex_yachtmaster.png"
        else:
            return "/static/images/watches/rolex_datejust.png"

    # Omega
    elif brand == "omega":
        if "seamaster" in name or "planet ocean" in name:
            return "/static/images/watches/omega_seamaster.png"
        elif "speedmaster" in name:
            return "/static/images/watches/omega_speedmaster.png"
        else:
            return "/static/images/watches/omega_constellation.png"

    # Tudor
    elif brand == "tudor":
        return "/static/images/watches/tudor_blackbay.png"

    # Breitling
    elif brand == "breitling":
        if "navitimer" in name:
            return "/static/images/watches/breitling_navitimer.png"
        return "/static/images/watches/breitling_chronomat.png"

    # Cartier
    elif brand == "cartier":
        return "/static/images/watches/cartier_dress.png"

    # IWC
    elif brand == "iwc":
        return "/static/images/watches/iwc_pilot.png"

    # Grand Seiko
    elif "grand seiko" in brand:
        return "/static/images/watches/grandseiko_sport.png"

    # Audemars Piguet
    elif "audemars" in brand:
        return "/static/images/watches/ap_royaloak.png"

    return "/static/images/watches/default_watch.png"

df["image_url"] = df.apply(img, axis=1)
df.to_csv("watches_final.csv", index=False)

print("Finished: watches_final.csv")