import requests

def fetch_coordinates(selected_id):
    api_url = f"https://www.wikidata.org/w/api.php" \
              f"?action=wbgetclaims" \
              f"&format=json" \
              f"&entity={selected_id}" \
              f"&property=P625"  # Property P625 represents coordinates

    response = requests.get(api_url)
    data = response.json()
    print(data)
    claims = data.get("claims", {})
    if "P625" in claims:
        coordinate_claims = claims["P625"]
        if coordinate_claims:
            coordinate_claim = coordinate_claims[0]  # Assuming there's only one claim

            main_snak = coordinate_claim.get("mainsnak", {})
            if main_snak.get("snaktype") == "value":
                coordinate_value = main_snak.get("datavalue", {}).get("value", {})

                latitude = coordinate_value.get("latitude")
                longitude = coordinate_value.get("longitude")

                coordinates = f"{latitude}, {longitude}"
                return coordinates

    return None  # Coordinates not found or couldn't be parsed

selected_id = "Q700614"  # Replace with the actual Wikidata ID
coordinates = fetch_coordinates(selected_id)
print(coordinates)
