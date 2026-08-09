// Report Doctor file-picker behavior regression test. Runs under plain
// `node tests/report_doctor_file_inputs_test.js` with no browser dependencies.
//
// Contract under test:
//  1. Each file picker has one unique id and exactly one label target.
//  2. report-doctor.js binds a change callback to each picker.
//  3. Selecting a file populates the corresponding JSON field.
'use strict';

var assert = require('assert');
var fs = require('fs');
var path = require('path');
var vm = require('vm');

function attributesFrom(source) {
  var attributes = {};
  var matches = source.matchAll(/\b([A-Za-z_:][\w:.-]*)\s*=\s*(["'])(.*?)\2/g);
  for (var match of matches) {
    attributes[match[1].toLowerCase()] = match[3];
  }
  return attributes;
}

function StubElement(tagName, attributes) {
  this.tagName = String(tagName || 'div').toUpperCase();
  this.attributes = attributes || {};
  this.childNodes = [];
  this.listeners = {};
  this.value = '';
  this.files = [];
  this._classes = new Set();
  this.classList = {
    add: this._classes.add.bind(this._classes),
    remove: this._classes.delete.bind(this._classes)
  };
}

Object.defineProperty(StubElement.prototype, 'firstChild', {
  get: function() { return this.childNodes.length ? this.childNodes[0] : null; }
});

Object.defineProperty(StubElement.prototype, 'textContent', {
  get: function() { return this._textContent || ''; },
  set: function(value) { this._textContent = String(value); }
});

StubElement.prototype.addEventListener = function(type, callback) {
  (this.listeners[type] = this.listeners[type] || []).push(callback);
};

StubElement.prototype.dispatch = function(type) {
  var callbacks = this.listeners[type] || [];
  for (var i = 0; i < callbacks.length; i++) callbacks[i].call(this);
};

StubElement.prototype.removeChild = function(child) {
  var index = this.childNodes.indexOf(child);
  if (index >= 0) this.childNodes.splice(index, 1);
  return child;
};

var html = fs.readFileSync(path.join(__dirname, '..', 'report-doctor.html'), 'utf8');
var elements = [];
var tagPattern = /<([A-Za-z][\w:.-]*)\b([^>]*)>/g;
for (var tagMatch of html.matchAll(tagPattern)) {
  elements.push(new StubElement(tagMatch[1], attributesFrom(tagMatch[2])));
}

var labels = elements.filter(function(element) {
  return element.tagName === 'LABEL';
});
var fileInputs = elements.filter(function(element) {
  return element.tagName === 'INPUT' && element.attributes.type === 'file';
});

fileInputs.forEach(function(input) {
  var id = input.attributes.id;
  assert.ok(id, 'every file input must have an id');

  var idTargets = elements.filter(function(element) {
    return element.attributes.id === id;
  });
  assert.strictEqual(
    idTargets.length,
    1,
    'file input #' + id + ' must be the only element with that id'
  );

  var matchingLabels = labels.filter(function(label) {
    return label.attributes.for === id;
  });
  assert.strictEqual(
    matchingLabels.length,
    1,
    'file input #' + id + ' must have exactly one label target'
  );
});

assert.deepStrictEqual(
  fileInputs.map(function(input) { return input.attributes.id; }).sort(),
  ['bootstrap-file', 'report-file'],
  'Report Doctor must expose one report picker and one optional bootstrap picker'
);

var documentStub = {
  getElementById: function(id) {
    for (var i = 0; i < elements.length; i++) {
      if (elements[i].attributes.id === id) return elements[i];
    }
    return null;
  },
  createElement: function(tagName) {
    return new StubElement(tagName, {});
  }
};

function StubFileReader() {
  this.result = '';
}

StubFileReader.prototype.readAsText = function(file) {
  this.result = file.contents;
  this.onload();
};

var script = fs.readFileSync(path.join(__dirname, '..', 'report-doctor.js'), 'utf8');
vm.runInNewContext(script, {
  document: documentStub,
  FileReader: StubFileReader,
  navigator: {},
  console: console,
  setTimeout: setTimeout
}, { filename: 'report-doctor.js' });

var pickerBehavior = [
  { picker: 'bootstrap-file', destination: 'bootstrap-json', contents: '{"schema":"bcs.parts_bootstrap/1.0","rows":[]}' },
  { picker: 'report-file', destination: 'report-json', contents: 'deliberately invalid report JSON' }
];

pickerBehavior.forEach(function(testCase) {
  var picker = documentStub.getElementById(testCase.picker);
  var destination = documentStub.getElementById(testCase.destination);
  assert.strictEqual(
    (picker.listeners.change || []).length,
    1,
    '#' + testCase.picker + ' must have exactly one change callback'
  );

  picker.files = [{ contents: testCase.contents }];
  picker.dispatch('change');
  assert.strictEqual(
    destination.value,
    testCase.contents,
    '#' + testCase.picker + ' must populate #' + testCase.destination
  );
});

console.log('PASS report_doctor_file_inputs_test: unique label targets and working callbacks');
