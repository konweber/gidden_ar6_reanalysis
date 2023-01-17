import itertools
import pathlib
import pyam # version: 1.4.1.dev15+g3563b43

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

#
# functions for figure 1
#

def make_quantiles(df, v, cat):
    data = (
        df
        .filter(region='World', variable=v)
        .filter(Category=cat)
        .compute.quantiles((0.1, 0.25, 0.5, 0.75, 0.9))
    )
    data.set_meta(cat, name='Category')
    data = data.rename({'model': {'Quantiles': cat}})
    return data

def make_sequestration_plot_data(df, variables, categories_to_temp, years=[2030, 2050]):
    # pyam version of quantile data
    data = pyam.concat([
        (
            df
            .filter(region='World', variable=variable)
            .filter(Category=category)
            .compute.quantiles((0.25, 0.5, 0.75))
            .rename(model={'Quantiles': temp})
        ) for (category, temp), variable in itertools.product(categories_to_temp.items(), variables)
    ])

    # data ready for plotting
    pdata = (
        data
        .filter(year=years)
        .as_pandas(meta_cols=False)
        .assign(index=lambda x: x.year.astype(str) + ' ' + x.model)
        .drop(columns=['region', 'unit', 'year', 'model'])
        .set_index(['index', 'scenario', 'variable'])
        ['value']
        .unstack(['scenario', 'variable'])
        / 1e3
    )
    pdata = pdata.reindex(index=pdata.index[::-1]) # reverse ordering so plots are in correct order
    return data, pdata

def sequestration_plot(pdata, order=None, medians=True, stacked=True, cmap='PiYG', ax=None, legend=None):
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 5))
    
    base, mins, maxs = pdata['0.5'], pdata['0.25'], pdata['0.75']
    if order:
        base = base[order]
    errors = [[base[c] - mins[c], maxs[c] - base[c]] for c in base.columns]
    
    base.plot.barh(xerr=errors, capsize=4, rot=0, stacked=stacked, ax=ax, cmap=cmap, alpha=0.7)
    if medians:
        ax.scatter(base.sum(axis=1), base.index, marker='s', color='k', label='Median Total')
    
    h, l = ax.get_legend_handles_labels()
    start = -1 * len(pdata.columns.get_level_values('variable').unique())
    if medians:
        start -= 1
    legend = legend or pyam.plotting.OUTSIDE_LEGEND['bottom']
    ax.legend(h[start:], l[start:], **legend)
    return ax

def share_of_cdr_data(df, categories_to_temp, offset=None, quantiles=(0.25, 0.5, 0.75)):
    variables = [
        'AR6 Reanalysis|OSCARv3.2|Carbon Removal', 
        'AR6 Reanalysis|OSCARv3.2|Carbon Removal|Land',
    ]
    dfs = []
    for cat, temp in categories_to_temp.items():
        data = (
            df
            .filter(variable=variables, region='World', year=range(2020, 2101, 10))
            .filter(Category=cat)
        )
        if offset:
            data = data.offset(year=offset)
        data = (
            data
            .divide(
                variables[1], variables[0],
                name='Land Share of Total CDR', ignore_units='fraction',
            )
            .compute.quantiles(quantiles)
            .rename({'model': {'Quantiles': temp}})
            .timeseries()
        )
        dfs.append(data)
    return pd.concat(dfs)

# 
# functions for figure 2
#

def make_gap_data(df, v, categories_to_temp):
    x = (
        df
        .filter(variable=v, year=[2030])
        .filter(Category=categories_to_temp.keys())
        .as_pandas()
        .replace({'Category': categories_to_temp})
    )
    idx = ['model', 'scenario', 'region', 'year', 'Category']
    x = x.set_index(idx)['value'] 
    return x

def make_gap_plot(data, drop={}, ax=None):
    data = data.reset_index().dropna()
    for col, value in drop.items():
        data = data[data[col] != value]
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 5))
    ax.axhline(0, c='k', ls='--', alpha=0.5)
    palette = {"2C": "#fc8d59", "1.5C":"#91bfdb"}
    sns.boxplot(
        x="region", y="value", hue="Category",
        data=data, 
        palette="Set2_r", ax=ax, showfliers=False, whis=0,
#        palette=palette, ax=ax, showfliers=False, whis=0,
    )
    return ax