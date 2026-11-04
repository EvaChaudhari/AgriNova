/**
 * Krishi Mitra (AgriNova) - Calibrated Baseline Regional Datasets
 * Based on Central Ground Water Board (CGWB), IMD Normals, and ICAR FAO-56 Benchmarks
 */

const MOCK_DATA = {
  bootstrap: {
    device_id: 'TEST-HARDWARE-UUID-001',
    is_onboarded: true,
    message: 'Device profile synchronized with live agro-climatic context.',
    profile: {
      device_id: 'TEST-HARDWARE-UUID-001',
      farmer_name: 'Rameshwar Patil (रामेश्वर पाटिल)',
      preferred_language: 'hi',
      phone_number: '+91 98765 43210',
      kisan_id: 'PMK-123456',
      created_at: '2026-06-01T08:00:00Z',
      updated_at: '2026-11-04T07:15:00Z'
    },
    active_plot_id: 1,
    hazard_state: 'NORMAL_MODE',
    enforced_restrictions: [],
    context: {
      device_id: 'TEST-HARDWARE-UUID-001',
      farmer_name: 'Rameshwar Patil',
      preferred_language: 'hi',
      plot_id: 1,
      plot_name: 'North Cotton Field (Warangal Plot)',
      centroid: { lat: 17.50045, lon: 78.50047 },
      area_hectares: 1.15,
      soil_texture: 'Vertisol',
      crop_name: 'Cotton',
      variety: 'Hybrid Bt-Cotton RCH-659',
      growth_stage: 'FLOWERING',
      days_after_sowing: 72,
      groundwater: {
        depth_mbgl: 11.2,
        source: 'CGWB_WARANGAL_MEDIAN',
        status: 'Safe (Adequate recharge buffer)'
      },
      soil_nutrients: {
        nitrogen_kg_ha: 220.0,
        phosphorus_kg_ha: 18.5,
        potassium_kg_ha: 310.0,
        ph: 7.8,
        organic_carbon_percent: 0.55,
        source: 'SOIL_HEALTH_CARD_BENCHMARK'
      },
      weather: {
        t_min: 22.4,
        t_max: 33.8,
        t_mean: 28.1,
        rh_mean: 68.0,
        wind_speed_2m: 2.1,
        rainfall_24h_mm: 0.0,
        seasonal_deficit_percent: -4.2,
        condition: 'Clear Sky with Mild Sunshine',
        source: 'IMD_AGROCLIMATIC_NORMAL'
      },
      satellite: {
        ndvi: 0.68,
        ndwi: 0.14,
        cloud_cover_percent: 8.5,
        source: 'SENTINEL_2_L2A_STAC',
        details: 'Healthy vegetative canopy with robust chlorophyll absorption and adequate leaf water content.'
      },
      hydrology: {
        et0_mm: 4.85,
        kc: 1.15,
        etc_mm: 5.58,
        root_depth_m: 1.2,
        taw_mm: 120.0,
        raw_mm: 78.0,
        depletion_mm: 42.5,
        trigger: 'HOLD',
        recommended_depth_mm: 0.0,
        efficiency: 0.90,
        details: 'Daily root zone depletion (42.5 mm) is within allowable buffering capacity (RAW = 78.0 mm). Soil moisture is adequate.'
      },
      hazard: {
        current_state: 'NORMAL_MODE',
        is_critical_water_stress: false,
        slope_risk: 'LOW_EROSION_RISK',
        enforced_restrictions: [],
        actionable_directives: [
          'Continue scheduled monitoring of flowering stage pests (bollworm monitoring).',
          'Maintain clean weed-free inter-row spaces to optimize soil moisture retention.',
          'Prepare drip fertigation cycle for potassium sulphate (K) application next week.'
        ],
        summary_message: 'Operating within safe agro-climatic envelope. No meteorological alerts.'
      }
    }
  },

  plots: [
    {
      id: 1,
      device_id: 'TEST-HARDWARE-UUID-001',
      name: 'North Cotton Field (Warangal Plot)',
      survey_number: '45/2',
      khasra_number: 'K-102',
      centroid_lat: 17.50045,
      centroid_lon: 78.50047,
      area_hectares: 1.15,
      soil_texture: 'Vertisol',
      elevation_m: 250.0,
      slope_percent: 1.5,
      is_active: true,
      boundary: {
        type: 'Polygon',
        coordinates: [
          [
            [78.5000, 17.5000],
            [78.50094, 17.5000],
            [78.50094, 17.5009],
            [78.5000, 17.5009],
            [78.5000, 17.5000]
          ]
        ]
      },
      crop_cycle: {
        id: 101,
        plot_id: 1,
        crop_name: 'Cotton',
        variety: 'Hybrid Bt-Cotton RCH-659',
        sowing_date: '2026-06-15',
        growth_stage: 'FLOWERING',
        irrigation_method: 'DRIP',
        is_active: true
      }
    },
    {
      id: 2,
      device_id: 'TEST-HARDWARE-UUID-001',
      name: 'South Paddy Field (Red Soil)',
      survey_number: '52/1',
      khasra_number: 'K-114',
      centroid_lat: 17.4981,
      centroid_lon: 78.5032,
      area_hectares: 0.85,
      soil_texture: 'Alfisol',
      elevation_m: 248.0,
      slope_percent: 0.8,
      is_active: false,
      boundary: {
        type: 'Polygon',
        coordinates: [
          [
            [78.5025, 17.4975],
            [78.5039, 17.4975],
            [78.5039, 17.4987],
            [78.5025, 17.4987],
            [78.5025, 17.4975]
          ]
        ]
      },
      crop_cycle: {
        id: 102,
        plot_id: 2,
        crop_name: 'Paddy',
        variety: 'MTU-1010',
        sowing_date: '2026-07-01',
        growth_stage: 'VEGETATIVE',
        irrigation_method: 'FLOOD',
        is_active: true
      }
    }
  ],

  // Sample chat history & deterministic query responder
  chatResponses: {
    irrigate_hi: {
      reply_text: 'किसान भाई, FAO-56 जल संतुलन गणना के अनुसार वर्तमान में जड़ क्षेत्र में 42.5 मिमी जल की कमी है, जो कि सुरक्षित सीमा (78 मिमी) के अंदर है। मिट्टी में पर्याप्त नमी मौजूद है, इसलिए आज सिंचाई करने की आवश्यकता नहीं है। 3 दिन बाद पुनः स्थिति जांची जाएगी।',
      hazard_state: 'NORMAL_MODE',
      injected_context: {
        crop_name: 'Cotton',
        growth_stage: 'FLOWERING',
        hydrology: { trigger: 'HOLD', recommended_depth_mm: 0.0 }
      }
    },
    irrigate_en: {
      reply_text: 'Farmer friend, based on the FAO-56 hydrological water balance model, your root zone depletion is currently 42.5 mm, which is well within the readily available water buffering capacity (78.0 mm). Soil moisture is healthy—HOLD irrigation today.',
      hazard_state: 'NORMAL_MODE',
      injected_context: {
        crop_name: 'Cotton',
        growth_stage: 'FLOWERING',
        hydrology: { trigger: 'HOLD', recommended_depth_mm: 0.0 }
      }
    },
    pest_hi: {
      reply_text: 'किसान भाई, पत्ती के लक्षणों में प्रारंभिक चूसक कीट (एफिड/थ्रिप्स) और हल्के अल्टरनेरिया धब्बे पाए गए हैं। CIB दिशा-निर्देशानुसार पहले गैर-रासायनिक उपचार करें: 5% नीम का तेल (NSKE) 50 मिली प्रति 15 लीटर टंकी में घोलकर छिड़कें। रासायनिक दवा की अभी जरूरत नहीं है।',
      hazard_state: 'NORMAL_MODE',
      injected_context: {
        crop_name: 'Cotton',
        growth_stage: 'FLOWERING',
        vision: { leaf_detected: true, detected_pathology: 'Thrips & Early Alternaria Blight' }
      }
    },
    pest_en: {
      reply_text: 'Based on leaf pathology screening compliant with CIB&RC IPM standards: Early sucking pest (thrips) infestation detected. Recommendation: Spray 5% Neem Seed Kernel Extract (NSKE) at 50ml per 15L knapsack tank. Install yellow sticky traps (10/acre). Avoid synthetic chemical spray at this threshold.',
      hazard_state: 'NORMAL_MODE',
      injected_context: {
        crop_name: 'Cotton',
        growth_stage: 'FLOWERING',
        vision: { leaf_detected: true, detected_pathology: 'Thrips & Early Alternaria Blight' }
      }
    },
    storm_alert_hi: {
      reply_text: 'सावधान किसान भाई! मौसम मॉडल के अनुसार भारी बारिश (50 मिमी+) का पूर्वानुमान है। STORM_FLOOD_MODE सक्रिय है। किसी भी कीटनाशक, फफूंदनाशक या यूरिया खाद का छिड़काव तुरंत रोक दें। खेत की मेड़ों के निकास नाले खोलें ताकि पानी न भरे।',
      hazard_state: 'STORM_FLOOD_MODE',
      injected_context: {
        hazard: {
          current_state: 'STORM_FLOOD_MODE',
          enforced_restrictions: ['HALT_ALL_CHEMICAL_SPRAYING', 'HALT_FERTILIZERS', 'CLEAR_DRAINAGE_FURROWS']
        }
      }
    }
  }
};

window.MOCK_DATA = MOCK_DATA;

