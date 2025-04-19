import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# 讀入資料（你應該會自己指定路徑）
df = pd.read_csv("123.csv")

# 篩選 put 與 call
df_put = df[df['option_type'] == 'put']
df_call = df[df['option_type'] == 'call']

# 建立 Pivot Table
put_oi_change = df_put.pivot(index='strike', columns='expiration', values='oi_abs_change')
call_oi_change = df_call.pivot(index='strike', columns='expiration', values='oi_abs_change')

# 計算差值：Call - Put
oi_diff = call_oi_change.fillna(0) - put_oi_change.fillna(0)

# 畫三張圖：Put、Call、Diff
fig, axes = plt.subplots(3, 1, figsize=(10, 16))

sns.heatmap(put_oi_change, cmap="YlOrBr", ax=axes[0])
axes[0].set_title("Put OI Absolute Change Heatmap")

sns.heatmap(call_oi_change, cmap="YlGnBu", ax=axes[1])
axes[1].set_title("Call OI Absolute Change Heatmap")

sns.heatmap(oi_diff, cmap="coolwarm", center=0, ax=axes[2])
axes[2].set_title("Call - Put OI Absolute Change Heatmap")

plt.tight_layout()
plt.show()

