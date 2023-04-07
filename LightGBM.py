import numpy as np
from sklearn.model_selection import LeaveOneOut
import pandas as pd
from sklearn.metrics import mean_squared_error
import lightgbm as lgb
import optuna
import matplotlib.pyplot as plt


def split(data):
    # print(data.shape)
    X = data.iloc[:,1:-1]
    y = data.iloc[:,-1]
    # print(X)
    # print(y)
    return X, y

def lightGBMLOO(data, params): 
    X, y = split(data)
    actual = y
    loo = LeaveOneOut()
    rmse, feature_importances = [], []
    predicted = np.zeros_like(y)

    lgb_model = lgb.LGBMRegressor(**params)

    print("Training Fold: ")
    for idx, (train_idx, test_idx) in enumerate(loo.split(X)):        
        print(idx, end=" ")
        # Get the training and testing data for the fold
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        # eval_set = [(X_test, y_test)]
        # Fit the LightGBM model to the training data
        lgb_model.fit(X_train, y_train) #eval_set=eval_set

        # Make predictions on the test data
        y_pred = lgb_model.predict(X_test)


        rmse.append( np.sqrt( mean_squared_error( y_test, y_pred )))
        
        feature_importances.append(lgb_model.feature_importances_)
        predicted[idx] = y_pred

    # Compute the accuracy metrics of the model using the predicted labels and true labels
    mrmse = np.mean(rmse)

    for idx, x in enumerate(predicted):
        predicted[idx] = np.mean(x)

    #print results
    print()
    print( ("-" * 12), "LightGBM", ("-" * 12) )
    print("RMSE: ", mrmse)

    # Plots
    fig, axs = plt.subplots(1, 2, figsize=(15, 5))
    
    mean_feature_importances = np.mean(feature_importances, axis=0)

    # Feature Importances
    axs[0].bar(X.columns, mean_feature_importances)
    axs[0].set_xticks(range(len(X.columns)))
    axs[0].set_xticklabels(X.columns, rotation=90, ha='right')
    axs[0].set_ylabel("Importance")
    axs[0].set_xlabel("Feature")
    axs[0].set_title("Feature Importances")

    # Residual Plot
    residuals = [a - p for a, p in zip(actual, predicted)]
    for idx, x in enumerate(residuals):
        residuals[idx] = x / len(residuals) #np.std(residuals)

    # = residuals / len(residuals)    #np.std(residuals)
    patient = np.arange(len(y))
    axs[1].scatter(patient, residuals)
    axs[1].set_xlabel("Patient")
    axs[1].set_ylabel("Actual-Pred / n")
    axs[1].set_title("Residual Plot")
    axs[1].axhline(y=0, color='blue', linestyle='-')

    # plt.tight_layout()
    plt.show()

    print("Feature Importance Values: ", *mean_feature_importances, sep=', ')


    # # Actual vs Predicted
    fig = plt.figure(figsize=(15, 5))
    bar_width = 0.4
    x = np.arange(len(actual))
    plt.bar(x - 0.2, actual, width=bar_width, label='Actual', color='deepskyblue')
    plt.bar(x + 0.2, predicted, width=bar_width, label='Predicted', color='steelblue')
    plt.legend()
    plt.xlabel("Patient")
    plt.ylabel("Value")
    plt.title("Actual vs Predicted")
    
    plt.show()
    
    rounded_actual = [round(num, 4) for num in actual]
    rounded_predicted = [round(num, 4) for num in predicted]
    print("Actual: ", *rounded_actual, sep=', ')
    print("Predct: ", *rounded_predicted, sep=', ')




def objectiveLOO(trial):
    # Set hyperparameters to be tuned
    params = {
        'objective': 'regression',
        'metric': 'rmse',
        'boosting_type': 'gbdt',
        'n_estimators': trial.suggest_int('n_estimators', 50, 500),
        'num_leaves': trial.suggest_int('num_leaves', 2, 256),
        'learning_rate': trial.suggest_float('learning_rate', 0.005, 2),
        'max_depth': trial.suggest_int('max_depth', -1, 30),
        'min_child_samples': trial.suggest_int('min_child_samples', 2, 6),
    } 

    data = pd.read_csv("selected_features.csv")
    X, y = split(data)
    loo = LeaveOneOut()
    rmse = []
    lgb_model = lgb.LGBMRegressor(**params)
                                      
    for idx, (train_idx, test_idx) in enumerate(loo.split(X)):        
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        lgb_model.fit(X_train, y_train) #eval_set=eval_set
        y_pred = lgb_model.predict(X_test)
        rmse.append( np.sqrt( mean_squared_error( y_test, y_pred )))

    mrmse = np.mean(rmse)
    # print("MRMSE From OPTUNA: ", mrmse)
    return mrmse

def lightGBMLOOOptuna(data, n):
    # Set up Optuna study and run optimization
    study = optuna.create_study(direction='minimize')
    study.optimize(objectiveLOO, n_trials=n)

    print("Best Parameters: ", study.best_params)
    print("Best Scorre:", study.best_value)

    lightGBMLOO(data, study.best_params)
