//VERSION=3
// Version "analitica" del script oficial "Cyanobacteria Chlorophyll-a NDCI L1C"
// (CyanoLakes, Kravitz & Matthews 2020) para Sentinel Hub.
// La logica (mascara de agua, FAI, NDCI, modelo de clorofila-a) es identica al
// script original en cyano_ndci_l1c_visual.js; unicamente se cambia la salida:
// en vez de una imagen RGB para visualizacion, retorna bandas float con los
// valores numericos (chl_a en ug/L, mascara de agua, FAI) para poder hacer
// estadistica y series de tiempo. Fuente del script original:
// https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/cyanobacteria_chla_ndci_l1c/

function setup() {
  return {
    input: ["B02", "B03", "B04", "B05", "B07", "B08", "B8A", "B11", "B12", "dataMask"],
    output: { bands: 4, sampleType: "FLOAT32" },
  };
}

var MNDWI_threshold = 0.42;
var NDWI_threshold = 0.4;
var filter_UABS = true;

function wbi(r, g, b, nir, swir1, swir2) {
  let ws = 0;
  try {
    var ndvi = (nir - r) / (nir + r),
      mndwi = (g - swir1) / (g + swir1),
      ndwi = (g - nir) / (g + nir),
      ndwi_leaves = (nir - swir1) / (nir + swir1),
      aweish = b + 2.5 * g - 1.5 * (nir + swir1) - 0.25 * swir2,
      aweinsh = 4 * (g - swir1) - (0.25 * nir + 2.75 * swir1);
    var dbsi = (swir1 - g) / (swir1 + g) - ndvi;
    if (
      mndwi > MNDWI_threshold ||
      ndwi > NDWI_threshold ||
      aweinsh > 0.1879 ||
      aweish > 0.1112 ||
      ndvi < -0.2 ||
      ndwi_leaves > 1
    ) {
      ws = 1;
    }
    if (filter_UABS && ws == 1) {
      if (aweinsh <= -0.03 || dbsi > 0) {
        ws = 0;
      }
    }
  } catch (err) {
    ws = 0;
  }
  return ws;
}

function FAI(a, b, c) {
  return b - a - ((c - a) * (783 - 665)) / (865 - 665);
}

function NDCI(a, b) {
  return (b - a) / (b + a);
}

function evaluatePixel(s) {
  let water = wbi(s.B04, s.B03, s.B02, s.B08, s.B11, s.B12);
  let FAIv = FAI(s.B04, s.B07, s.B8A);
  let NDCIv = NDCI(s.B04, s.B05);
  let chl = 826.57 * NDCIv ** 3 - 176.43 * NDCIv ** 2 + 19 * NDCIv + 4.071;

  // El script original (visual) solo define colores para chl en [0, 500] ug/L
  // (satura en los extremos); replicamos ese mismo rango aqui para la salida
  // numerica, ya que fuera de el el modelo cubico de NDCI dejar de ser
  // fisicamente interpretable (pixeles de agua mixtos/turbios en el borde).
  let chl_clip = Math.max(0, Math.min(500, chl));

  // banda 0: chl-a (ug/L) solo sobre agua, NaN fuera de agua o floracion flotante (FAI>0.08)
  // banda 1: mascara de agua (0/1)
  // banda 2: FAI (indice de vegetacion flotante)
  // banda 3: dataMask (validez del pixel, nubes/borde de escena)
  let chl_out = water == 1 && FAIv <= 0.08 ? chl_clip : NaN;
  return [chl_out, water, FAIv, s.dataMask];
}
