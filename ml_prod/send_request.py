import requests

def predict_house_prices(houses):
    url = "http://127.0.0.1:8000/predict"
    response = requests.post(url, json=houses)
    if response.status_code == 200:
        house_predictions = response.json()
        print("Prédictions de prix de maisons :")
        for pred in house_predictions:
            print(pred)
    else:
        print("Erreur sur /predict :", response.status_code)

def predict_tumors(tumors):
    url = "http://127.0.0.1:8000/tumor"
    response = requests.post(url, json=tumors)
    if response.status_code == 200:
        tumor_predictions = response.json()
        print("\nPrédictions de tumeurs :")
        for pred in tumor_predictions:
            print(pred)
    else:
        print("Erreur sur /tumor :", response.status_code)

if __name__ == "__main__":
    houses_data = [
        {"taille": 100, "nb_chambres": 3, "jardin": 1},
        {"taille": 80, "nb_chambres": 2, "jardin": 0}
    ]
    predict_house_prices(houses_data)

    tumor_data = [
        {"size": 0.04, "p53_concentration": 0.012},
        {"size": 0.20, "p53_concentration": 0.9},
        {"size": 0.012898248148738226, "p53_concentration": 0.0018985663081065498}

    ]
    predict_tumors(tumor_data)
