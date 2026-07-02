# Master Data Dictionary

*Note: All string categories (e.g., `cms_state`, `cms_specialty`, `gender`) have been cleanly `encoded` into Stata integers with attached value labels for memory efficiency.*

## 1. The Base Grain (Individual Provider Metrics)
Variables lacking a prefix represent the individual physician/practitioner (`npi`). We utilize a "Golden Schema" (`partd_` for pharmacy, `partb_` for clinical services) to strictly track the origin of the data.

### 1a. Absolute Rates (Systemic Utilization)
Measures the provider's general reliance on a specific behavior relative to their *entire* patient volume.
| Variable | Description |
| :--- | :--- |
| `partd_generic_rate` | Ratio of generic drug claims to total Part D claims. |
| `partd_high_cost_rate` | Proportion of prescribed drugs in the top 25th cost percentile for their empirical class. |
| `partd_opioid_rate` | Ratio of all opioid claims to total Part D claims. |
| `partb_low_value_rate` | Ratio of *Choosing Wisely* low-value services (e.g., unnecessary joint injections) to total Part B services. |
| `partb_imaging_adv_rate` | Ratio of advanced imaging (MRIs/CTs) to total Part B services. |

### 1b. Conditional Rates (Severity Preference & Upcoding)
Measures the provider's intensity or severity preference *conditional* on already choosing to treat within a specific clinical lane.
| Variable | Description |
| :--- | :--- |
| `partd_opioid_strong_rate` | Ratio of Schedule II (Strong) opioids to total opioid claims. |
| `partb_em_upcode_rate` | Ratio of Level 4 & 5 E&M claims to total E&M claims. |
| `partb_imaging_cond_rate` | Ratio of advanced imaging to total imaging services (leveraging RBCS taxonomy). |

## 2. The Facility Environment (`fac_` Namespace)
These variables exist on the individual provider panel but represent the **aggregate averages** of the hospital (`ccn`) where the provider works. 

| Variable | Description |
| :--- | :--- |
| `fac_tot_benes` | The total Medicare footprint (beneficiaries) of the hospital's affiliated network. |
| `fac_mean_[rate]` | The simple, unweighted average rate of the hospital's affiliated doctors. |
| `fac_wgt_[rate]` | The volume-weighted average rate of the hospital. *Note: Weighted specifically by the exact denominator of the rate (e.g., `fac_wgt_em_upcode_rate` is weighted by E&M visits, not total visits).* |

## 3. Hospital Consumer Assessment (`hcahps_` Namespace)
Derived from HCAHPS Patient Surveys and Inpatient Quality Reporting (IQR).

| Variable | Description |
| :--- | :--- |
| `h_comp_1_a_p` | % of patients who reported nurses "Always" communicated well. |
| `h_hosp_rating_9_10` | % rating the hospital a 9 or 10 overall. |
| `rrp_excess_ratio_ami` | Readmission Reduction Program ratio for Heart Attacks. `> 1.0` triggers a penalty. |
| `hac_total_score` | Hospital-Acquired Condition Score (1-10). **Higher is worse.** |

## 4. MACRA & QPP Performance (`mips_` Namespace)
Derived from the Merit-based Incentive Payment System. Range: 0-100.

| Variable | Description |
| :--- | :--- |
| `mips_final_score` | The composite score dictating the clinician's Part B payment adjustment. |
| `mips_quality_score` | Performance on clinical outcome and process measures. |
| `mips_cost_score` | Risk-adjusted resource utilization. Often missing during 2020-2021 (EUC). |
| `fac_mips_final_score` | The beneficiary-volume-weighted average MIPS score of the hospital's staff. |

## 5. Ambulatory Surgical Center Quality (`asc_rate_` Namespace)
Outpatient ASC market-level metrics. Rates are per 1,000 admissions unless otherwise noted. ASC files begin in 2015 marking the inception of robust ASCQR reporting.

| Variable | Description |
| :--- | :--- |
| `asc_rate_1` | Patient Burn rate per 1,000 admissions. |
| `asc_rate_2` | Patient Fall rate per 1,000 admissions. |