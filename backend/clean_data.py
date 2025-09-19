import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import scipy.io

def mat_to_dataframe(mat_path):
    
    mat = scipy.io.loadmat(mat_path, struct_as_record=False, squeeze_me=True)
    battery_key = [k for k in mat.keys() if not k.startswith('__')][0]
    battery = mat[battery_key]

    cycles = battery.cycle
    if not isinstance(cycles, np.ndarray):
        cycles = np.array([cycles])

    rows = []
    for i, cycle in enumerate(cycles):
        cycle_type = getattr(cycle, 'type', None)
        ambient_temperature = getattr(cycle, 'ambient_temperature', None)
        time = getattr(cycle, 'time', None)
        data = getattr(cycle, 'data', None)
        if data is None:
            continue
        if isinstance(data, np.ndarray):
            data_list = data
        else:
            data_list = [data]

        for entry in data_list:
            row = {
                'cycle_index': i,
                'cycle_type': cycle_type,
                'ambient_temperature': ambient_temperature,
                'time': time
            }
            for field in entry._fieldnames:
                row[field] = getattr(entry, field)
            rows.append(row)

    df = pd.DataFrame(rows)
    return df

def clean_and_normalize_battery_df(df):
   
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].interpolate(method="linear", limit_direction="both")
            df[col] = df[col].ffill().bfill()
        else:
            def fix_obj(x):
                if x is None or (isinstance(x, float) and pd.isna(x)):
                    return []
                if isinstance(x, (list, np.ndarray)):
                    return [abs(i) if isinstance(i, complex) else i for i in x]
                if isinstance(x, str):
                    return x if x.strip() != "" else []
                return []
            df[col] = df[col].apply(fix_obj)

    
    list_cols = [col for col in df.columns if isinstance(df[col].iloc[0], list)]
    for col in list_cols:
        df[col + '_mean'] = df[col].apply(lambda x: np.mean(x) if len(x) > 0 else np.nan)
        df[col + '_max'] = df[col].apply(lambda x: np.max(x) if len(x) > 0 else np.nan)
        df[col + '_min'] = df[col].apply(lambda x: np.min(x) if len(x) > 0 else np.nan)
        df[col + '_std'] = df[col].apply(lambda x: np.std(x) if len(x) > 0 else np.nan)
    df.drop(columns=list_cols, inplace=True)

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        mean_val = df[col].mean()
        df[col] = df[col].fillna(mean_val)


    def remove_outliers(series):
        if pd.api.types.is_numeric_dtype(series):
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            if pd.isna(IQR) or IQR == 0:
                return series
            lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
            return np.clip(series, lower, upper)
        return series
    df = df.apply(remove_outliers)

   
    scaler = MinMaxScaler()
    df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
    return df


def load_clean_battery(mat_path):
   
    df = mat_to_dataframe(mat_path)
    df_clean = clean_and_normalize_battery_df(df)
    return df_clean
