"""Phase 6.4: fit frozen Phase 6.3 spatial RFs; never revisit raw recordings."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from dm8_modeling.rf.dog import GaussianGrid, lofo_training, projection_matrix, rotational_profile
from dm8_modeling.rf.population import radial_profile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def number(value):
    return '' if value is None else value


def fit_row(unit, representation, fit):
    return dict(unit=unit, representation=representation, model=fit.model,
                n_points=len(fit.prediction), SSE=fit.sse, R2=fit.r2, AIC=fit.aic,
                AICc=fit.aicc, BIC=fit.bic, baseline=fit.baseline,
                center_amplitude=fit.a1, center_sigma_px=number(fit.sigma1),
                surround_amplitude=number(fit.a2), surround_sigma_px=number(fit.sigma2),
                relative_surround_amplitude=number(None if fit.a2 is None or abs(fit.a1) < 1e-12
                                                   else fit.a2 / abs(fit.a1)),
                parameter_at_bound=fit.at_bound, fit_status=fit.status,
                near_optimal_surround_sigma_min_px=number(fit.near_sigma2_min),
                near_optimal_surround_sigma_max_px=number(fit.near_sigma2_max),
                near_optimal_surround_amplitude_min=number(fit.near_a2_min),
                near_optimal_surround_amplitude_max=number(fit.near_a2_max))


def diagram(path, draw):
    fig = plt.figure(figsize=(9, 5))
    draw(fig)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def draw_figures(out, x, data, fits, radial, lofo, null_delta, obs_delta):
    colors = plt.get_cmap('tab10').colors
    def f1(fig):
        ax = fig.add_subplot(111)
        for i in range(5): ax.plot(x, data[f'fly{i+1}'], color=colors[i], alpha=.75, label=f'fly{i+1}')
        ax.plot(x, data['population'], color='black', linewidth=3, label='equal-fly population')
        ax.set(xlabel='Position (grid px)', ylabel='Rotational 1D RF (signed)', title='Figure 1 · Li-style rotation/projection')
        ax.legend(ncol=3)
    diagram(out/'figure_01_projection.png', f1)
    def f2(fig):
        ax=fig.add_subplot(111); ax.plot(x,data['population'],'ko-',label='observed')
        for model in ('M0','M1','M2','M3'):
            ax.plot(x,fits['population'][model].prediction,label=model)
        ax.set(xlabel='Position (grid px)',ylabel='Signed RF',title='Figure 2 · Population model fits');ax.legend()
    diagram(out/'figure_02_population_models.png',f2)
    def f3(fig):
        axs=fig.subplots(2,3).ravel()
        for i in range(5):
            unit=f'fly{i+1}';a=axs[i];a.plot(x,data[unit],'ko-',markersize=2,label='RF')
            for model in ('M1','M3'):a.plot(x,fits[unit][model].prediction,label=model)
            a.set_title(unit);a.axhline(0,color='.7',linewidth=.5)
        axs[5].axis('off');axs[0].legend();fig.suptitle('Figure 3 · Each fly: M1 vs M3')
    diagram(out/'figure_03_fly_fits.png',f3)
    def f4(fig):
        ax=fig.add_subplot(111);units=[f'fly{i}' for i in range(1,6)]+['population']
        xx=np.arange(len(units));ax.bar(xx-.18,[fits[u]['M1'].aicc-fits[u]['M3'].aicc for u in units],.36,label='ΔAICc')
        ax.bar(xx+.18,[fits[u]['M1'].bic-fits[u]['M3'].bic for u in units],.36,label='ΔBIC')
        ax.axhline(0,color='black',linewidth=.7);ax.set_xticks(xx,units)
        ax.set(ylabel='M1 minus M3 (positive favors M3)',title='Figure 4 · Fly-level comparison');ax.legend()
    diagram(out/'figure_04_information_criteria.png',f4)
    def f5(fig):
        ax=fig.add_subplot(111);units=[f'fly{i}' for i in range(1,6)];xx=np.arange(5)
        for k,model in enumerate(('M1','M3')):
            ax.bar(xx+(.35*k-.175),[next(r['heldout_SSE'] for r in lofo if r['heldout_fly']==u and r['model']==model) for u in units],.35,label=model)
        ax.set_xticks(xx,units);ax.set(ylabel='Held-out SSE',title='Figure 5 · Leave-one-fly-out generalization');ax.legend()
    diagram(out/'figure_05_lofo.png',f5)
    def f6(fig):
        ax=fig.add_subplot(111)
        for i in range(5):
            u=f'fly{i+1}';ax.plot(x,data[u]-fits[u]['M1'].prediction,color=colors[i],label=u)
        for u,style in (('population','black'),('stable_population','purple')):
            ax.plot(x,data[u]-fits[u]['M1'].prediction,color=style,linewidth=2.5,label=u)
        ax.axhline(0,color='black',linewidth=.5);ax.set(xlabel='Position (grid px)',ylabel='M1 residual',title='Figure 6 · Shared broad residual?');ax.legend(ncol=3)
    diagram(out/'figure_06_m1_residuals.png',f6)
    def f7(fig):
        ax=fig.add_subplot(111);units=[f'fly{i}' for i in range(1,6)]+['population','stable_population']
        for i,u in enumerate(units):
            f=fits[u]['M3'];ax.plot([f.near_sigma2_min,f.near_sigma2_max],[i,i],color='gray',linewidth=4)
            ax.plot(f.sigma2,i,'o',color='red' if f.at_bound else 'blue')
        ax.axvline(7,color='red',linestyle='--');ax.set_yticks(range(len(units)),units)
        ax.set(xlabel='Surround σ (grid px); line = ΔAICc ≤ 2 profile',title='Figure 7 · Surround width identifiability')
    diagram(out/'figure_07_parameter_stability.png',f7)
    def f8(fig):
        ax=fig.add_subplot(111);units=[f'fly{i}' for i in range(1,6)]+['population'];xx=np.arange(6)
        for k,prefix in enumerate(('', 'stable_')):
            ax.bar(xx+(.35*k-.175),[fits[prefix+u]['M1'].aicc-fits[prefix+u]['M3'].aicc for u in units],.35,label='stable' if prefix else 'all')
        ax.set_xticks(xx,units);ax.axhline(0,color='black',linewidth=.7)
        ax.set(ylabel='ΔAICc M1−M3',title='Figure 8 · Stable-center sensitivity');ax.legend()
    diagram(out/'figure_08_stable_sensitivity.png',f8)
    def f9(fig):
        ax=fig.add_subplot(111);ax.hist(null_delta,bins=35,color='.55');ax.axvline(obs_delta,color='red',linewidth=2,label=f'observed {obs_delta:.2f}')
        ax.set(xlabel='ΔAICc M1−M3',ylabel='Null count',title='Figure 9 · Phase 6.3 full-pipeline null');ax.legend()
    diagram(out/'figure_09_null_delta.png',f9)
    def supp(fig):
        ax=fig.add_subplot(111);u='population'
        ax.plot(x,data[u],label='rotational projection')
        ax.plot(radial[u][0],radial[u][1],label='radial average')
        ax.set(xlabel='Signed distance / radial bin (grid px)',ylabel='Signed RF',title='Supplement · Representation sensitivity');ax.legend()
    diagram(out/'supp_radial_profile.png',supp)


def run(root):
    root=Path(root).resolve()
    config_path=root/'configs/phase6_4_dog_test.json'
    config=json.loads(config_path.read_text())
    input_path=root/config['phase63_arrays']
    if digest(input_path)!=config['phase63_arrays_sha256']:
        raise ValueError('Phase 6.3 frozen input hash mismatch')
    before=digest(input_path); config_hash=digest(config_path)
    out=root/'docs/phase6_4_results';out.mkdir(exist_ok=True)
    projector=projection_matrix(15,config['rotation_steps'])
    x=np.asarray(config['x_positions_px'],float)
    grid=GaussianGrid(x,config)
    with np.load(input_path) as z:
        fly=z['fly_maps'].copy()
        stable=z['group_bins'][:,1].mean(axis=1)
        null=z['null_population'].copy()
        edges=z['radial_edges'].copy()
    maps={f'fly{i+1}':fly[i] for i in range(5)}
    maps['population']=fly.mean(axis=0)
    maps.update({f'stable_fly{i+1}':stable[i] for i in range(5)})
    maps['stable_population']=stable.mean(axis=0)
    data={u:rotational_profile(image,projector) for u,image in maps.items()}
    radial={}
    for u,image in maps.items():
        profile,_=radial_profile(image,edges)
        valid=np.isfinite(profile)
        radial[u]=(((edges[:-1]+edges[1:])/2)[valid],profile[valid])
    models=('M0','M1','M2','M3')
    fits={u:{m:grid.fit(y,m) for m in models} for u,y in data.items()}
    radial_fits={u:{m:GaussianGrid(radial[u][0],config).fit(radial[u][1],m) for m in models} for u in maps}
    comparison=[fit_row(u,representation,fit) for representation,group in (('LI_STYLE_1D_PROJECTION',fits),('RADIAL_AVERAGE',radial_fits))
                for u,unit in group.items() for fit in unit.values()]
    table(out/'model_comparison.csv',comparison)
    lofo=[]
    for i in range(5):
        held=f'fly{i+1}'
        training=lofo_training(np.stack([data[f'fly{j+1}'] for j in range(5)]),i)
        training_m1=grid.fit(training,'M1')
        shared_variance=max(training_m1.sse/len(x),1e-12)
        for model in ('M1','M2','M3'):
            fit=grid.fit(training,model)
            error=data[held]-fit.prediction
            sse=float(error@error)
            lofo.append(dict(heldout_fly=held,model=model,training_flies=','.join(f'fly{j+1}' for j in range(5) if j!=i),
                             training_weight='equal_fly',training_SSE=fit.sse,heldout_SSE=sse,
                             heldout_MSE=sse/len(x),heldout_correlation=float(np.corrcoef(data[held],fit.prediction)[0,1]),
                             heldout_gaussian_NLL=0.5*len(x)*np.log(2*np.pi*shared_variance)+sse/(2*shared_variance),
                             common_training_M1_variance=shared_variance))
    table(out/'lofo_model_comparison.csv',lofo)
    stability=[]
    for u,group in fits.items():
        for model in ('M2','M3'):
            f=group[model]
            stability.append(dict(unit=u,model=model,center_amplitude=f.a1,center_sigma_px=f.sigma1,
                                  surround_amplitude=f.a2,surround_sigma_px=f.sigma2,
                                  relative_surround_amplitude=number(None if abs(f.a1)<1e-12 else f.a2/abs(f.a1)),
                                  near_optimal_sigma_min_px=f.near_sigma2_min,near_optimal_sigma_max_px=f.near_sigma2_max,
                                  near_optimal_amplitude_min=f.near_a2_min,near_optimal_amplitude_max=f.near_a2_max,
                                  parameter_at_bound=f.at_bound,fit_status=f.status))
    table(out/'parameter_stability.csv',stability)
    profiles=[]
    for representation, group_data, group_fits, positions in (('LI_STYLE_1D_PROJECTION',data,fits,{u:x for u in maps}),
                                                             ('RADIAL_AVERAGE',{u:v[1] for u,v in radial.items()},radial_fits,{u:v[0] for u,v in radial.items()})):
        for u,y in group_data.items():
            for k,(position,value) in enumerate(zip(positions[u],y,strict=True)):
                profiles.append(dict(unit=u,representation=representation,position_px=position,observed=value,
                                     M0=group_fits[u]['M0'].prediction[k],M1=group_fits[u]['M1'].prediction[k],
                                     M2=group_fits[u]['M2'].prediction[k],M3=group_fits[u]['M3'].prediction[k],
                                     M1_residual=value-group_fits[u]['M1'].prediction[k]))
    table(out/'profiles.csv',profiles)
    null_profiles=null.reshape(len(null),225)@projector.T
    observed_delta=fits['population']['M1'].aicc-fits['population']['M3'].aicc
    null_rows=[]
    for index,y in enumerate(null_profiles):
        m1=grid.fit(y,'M1');m3=grid.fit(y,'M3')
        null_rows.append(dict(iteration=index,kind='phase63_full_pipeline_null',M1_AICc=m1.aicc,M3_AICc=m3.aicc,
                              delta_AICc_M1_minus_M3=m1.aicc-m3.aicc,M1_SSE=m1.sse,M3_SSE=m3.sse,
                              M3_surround_amplitude=m3.a2,M3_surround_sigma_px=m3.sigma2,M3_status=m3.status))
    null_rows.append(dict(iteration='observed',kind='observed',M1_AICc=fits['population']['M1'].aicc,
                          M3_AICc=fits['population']['M3'].aicc,delta_AICc_M1_minus_M3=observed_delta,
                          M1_SSE=fits['population']['M1'].sse,M3_SSE=fits['population']['M3'].sse,
                          M3_surround_amplitude=fits['population']['M3'].a2,
                          M3_surround_sigma_px=fits['population']['M3'].sigma2,
                          M3_status=fits['population']['M3'].status))
    table(out/'null_model_comparison.csv',null_rows)
    null_delta=np.array([r['delta_AICc_M1_minus_M3'] for r in null_rows[:-1]])
    draw_figures(out,x,data,fits,radial,lofo,null_delta,observed_delta)
    lofo_relative={f'fly{i}':(next(r['heldout_SSE'] for r in lofo if r['heldout_fly']==f'fly{i}' and r['model']=='M1')-
                              next(r['heldout_SSE'] for r in lofo if r['heldout_fly']==f'fly{i}' and r['model']=='M3'))/
                              next(r['heldout_SSE'] for r in lofo if r['heldout_fly']==f'fly{i}' and r['model']=='M1')
                   for i in range(1,6)}
    summary=dict(phase63_input_sha256=before,phase64_config_sha256=config_hash,biological_n=5,
                 primary_representation=config['representation_primary'],
                 observed_delta_AICc=observed_delta,
                 observed_null_upper_tail=(1+int(np.sum(null_delta>=observed_delta)))/(len(null_delta)+1),
                 null_delta_quantiles=np.quantile(null_delta,[.025,.5,.975]).tolist(),
                 lofo_m3_relative_SSE_improvement=lofo_relative,
                 result_tables=['model_comparison.csv','lofo_model_comparison.csv','parameter_stability.csv',
                                'null_model_comparison.csv','profiles.csv'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=lambda o:bool(o) if isinstance(o,np.bool_) else float(o)))
    if digest(input_path)!=before or digest(config_path)!=config_hash:
        raise RuntimeError('Frozen input/config changed while fitting')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-root',type=Path,default=Path.cwd())
    args=parser.parse_args()
    run(args.workspace_root)
