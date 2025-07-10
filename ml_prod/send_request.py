import requests

def predict_house_prices(houses):
    url = "http://127.0.0.1:8000/predict"
    response = requests.post(url, json=houses)
    if response.status_code == 200:
        return response.json()
    else:
        print("Erreur sur /predict :", response.status_code)
        return None

def predict_tumors(tumors):
    url = "http://127.0.0.1:8000/tumor"
    response = requests.post(url, json=tumors)
    if response.status_code == 200:
        return response.json()
    else:
        print("Erreur sur /tumor :", response.status_code)
        return None

if __name__ == "__main__":
    houses_data = [
        {"taille": 100, "nb_chambres": 3, "jardin": 1},
        {"taille": 80, "nb_chambres": 2, "jardin": 0}
    ]
    house_predictions = predict_house_prices(houses_data)
    if house_predictions:
        print("Prédictions de prix de maisons :")
        for pred in house_predictions:
            print(pred)

    tumor_data = [
        {"size": 0.04, "p53_concentration": 0.012},
        {"size": 0.20, "p53_concentration": 0.9}
    ]
    tumor_predictions = predict_tumors(tumor_data)
    if tumor_predictions:
        print("\nPrédictions de tumeurs :")
        for pred in tumor_predictions:
            print(pred)
