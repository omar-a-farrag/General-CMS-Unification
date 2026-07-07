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
| `partd_opioid_strong_rate` | Ratio of Schedule II narcotics to total opioid claims. |
| `partb_em_upcode_rate` | Ratio of Level 4/5 E&M visits to total E&M visits. |

## 2. Inpatient Quality & Value-Based Purchasing
Extracted from Hospital Compare and HVBP datasets.
| Variable | Description |
| :--- | :--- |
| `totalperformance_score` | HVBP Total Performance Score (TPS) driving inpatient payment penalties/bonuses. |
| `mspb_score` | Medicare Spending Per Beneficiary score (Efficiency domain). |
| `mortality_rate_[cond]` | 30-Day Mortality Rate for AMI, HF, or PN. |
| `rrp_excess_ratio_[cond]` | Hospital Readmissions Reduction Program excess readmission ratio. |
| `hac_total_score` | Hospital-Acquired Condition (HAC) Reduction Program penalty score. |
| `paym_30_[cond]` | Average Medicare payment category for 30-day episodes. |

## 3. Hospital Outpatient Department (HOPD) Quality
Extracted from Outpatient Quality Reporting (OQR) datasets.
| Variable | Description |
| :--- | :--- |
| `op_8` | MRI Lumbar Spine for Low Back Pain (Overuse metric). |
| `op_22` | Percentage of patients who left the Emergency Department without being seen. |
| `op_26` | Total Outpatient Surgical Procedure Volume (Aggregated across 9 anatomical categories). |
| `op_40` | STEMI Clinical Quality Measure. |
| `oas_rating_linear` | HOPD OAS CAHPS: Linear Mean Rating (0-100). |
| `oas_recmnd_linear` | HOPD OAS CAHPS: Linear Mean Willingness to Recommend (0-100). |

## 4. Ambulatory Surgical Center (ASC) Quality
Derived from the ASCQR Program. In the Provider files, these variables are prefixed with `zip_` to indicate they are localized geographic market averages, serving as proxies for outpatient competition and satisfaction.
| Variable | Description |
| :--- | :--- |
| `asc_1` / `zip_asc_1` | Patient Burn Rate. |
| `asc_2` / `zip_asc_2` | Patient Fall Rate. |
| `asc_3` / `zip_asc_3` | Wrong Site, Wrong Side, Wrong Patient, Wrong Procedure, Wrong Implant. |
| `asc_4` / `zip_asc_4` | All-Cause Hospital Transfer/Admission. |
| `asc_8` / `zip_asc_8` | Influenza Vaccination Coverage among ASC Personnel. |
| `oas_rating_linear` / `zip_oas_...`| ASC OAS CAHPS: Linear Mean Rating (0-100). |

## 5. Facility-Level Proxies (`fac_` Namespace)
Because CMS evaluates clinical quality primarily at the facility level, we attribute hospital or localized market averages back to individual clinicians.
| Variable | Description |
| :--- | :--- |
| `fac_mips_final_score` | The volume-weighted average MIPS score of a facility. For inpatient, this is the hospital staff's average. For outpatient, this represents the average score of all ASC providers operating in that localized ZIP-code market. |

## 6. Clinical Productivity and Scale (RVUs)
Mapped dynamically using the Q1 CMS Physician Fee Schedule to hold intra-year billing weights constant. RVUs replace raw claim counts to isolate true effort and resource intensity.
| Variable | Description |
| :--- | :--- |
| `partb_rvu_work` | Provider Work RVU. A mathematically pure measure of the physician's cognitive effort, time, and clinical intensity, stripping away facility overhead. |
| `fac_total_work_rvu` | Aggregated Hospital Work RVU. Captures the total clinical effort footprint of all affiliated providers. |
| `fac_total_fac_rvu` | Hospital Total RVU (Work + Facility PE + Malpractice). The resource-weighted measure of total institutional operational scale and overhead. |
| `partb_rvu_nonfac_total` | Office Baseline RVU (Work + Non-Facility PE + MP). Tracks total resource intensity for independent community practices. |

## 7. Geographic Market Definitions
Derived from the Dartmouth Atlas of Health Care to structure demand-side models.
| Variable | Description |
| :--- | :--- |
| `hsanum` | Hospital Service Area (HSA). Local health care markets for primary and basic hospital care. |
| `hrrnum` | Hospital Referral Region (HRR). Regional health care markets for tertiary care and major cardiovascular/surgical interventions. |