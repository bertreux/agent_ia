def build_model():
    import pandas as pd
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.model_selection import train_test_split
    import joblib
    from sklearn.preprocessing import MinMaxScaler

    df = pd.read_csv('tumor_two_vars.csv')
    X = df[['size', 'p53_concentration']]
    y = df['is_cancerous']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = MinMaxScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    model = DecisionTreeClassifier(random_state=0)
    model.fit(X_train_scaled, y_train)
    joblib.dump((model, scaler), "tumor.joblib")

build_model()
