/**
 * Vértice · Puente a Google Drive
 *
 * Recibe los archivos del proyecto del día desde GitHub Actions y los guarda en
 *   Vértice - Proyectos del día / <clave> / Anteproyecto | Proyecto ejecutivo / ...
 *
 * Instalación (una sola vez):
 *  1. script.google.com → Nuevo proyecto → pega este código.
 *  2. Configuración del proyecto (engrane) → Propiedades del script → agrega
 *        VERTICE_TOKEN = (el token que te dio Claude; también va en el secreto de GitHub)
 *  3. Implementar → Nueva implementación → tipo "Aplicación web"
 *        Ejecutar como: Yo · Quién tiene acceso: Cualquier usuario
 *     Autoriza el acceso a Drive y copia la URL /exec (va en el secreto VERTICE_DRIVE_URL).
 */
var CARPETA_RAIZ = '1uHcG0rPvMFb1X4J6jX1liowd2Kx6Ekhh';   // Vértice - Proyectos del día

function doPost(e) {
  var d = JSON.parse(e.postData.contents);
  var token = PropertiesService.getScriptProperties().getProperty('VERTICE_TOKEN');
  if (!token || d.token !== token) {
    return salida({ ok: false, error: 'token inválido' });
  }
  var carpeta = DriveApp.getFolderById(CARPETA_RAIZ);
  (d.ruta || []).forEach(function (nombre) { carpeta = subcarpeta(carpeta, nombre); });
  var existentes = carpeta.getFilesByName(d.nombre);
  while (existentes.hasNext()) { existentes.next().setTrashed(true); }   // reemplaza la versión anterior
  var blob = Utilities.newBlob(Utilities.base64Decode(d.base64), d.mime || 'application/octet-stream', d.nombre);
  var archivo = carpeta.createFile(blob);
  return salida({ ok: true, id: archivo.getId(), url: archivo.getUrl(), carpeta: carpeta.getUrl() });
}

function doGet() {
  return salida({ ok: true, servicio: 'Vértice · Puente a Drive' });
}

function subcarpeta(padre, nombre) {
  var it = padre.getFoldersByName(nombre);
  return it.hasNext() ? it.next() : padre.createFolder(nombre);
}

function salida(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
