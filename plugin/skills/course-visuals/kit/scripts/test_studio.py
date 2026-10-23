#!/usr/bin/env python3
"""test_studio.py - the figure studio draws one spec, audits every step at both sizes and photographs it, and the
kit's own layout moves a label off a part by itself (2.48.0). Run: python test_studio.py  (SKIP without Chrome/Edge)"""
from __future__ import annotations

import html
import io
import json
import os
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import studio  # noqa: E402

FAILS = []


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


# a valve whose name the spec puts right on the tank under it, and a room's name inside it: the layout must move the
# first clear of the tank and keep the second inside its room
GOOD = {"size": [520, 300], "label": "studio test", "parts": [
    {"id": "R", "type": "space", "x": 20, "y": 20, "w": 480, "h": 260, "label": "FUEL PREPARATION ROOM"},
    {"id": "T", "type": "tank", "x": 60, "y": 120, "w": 260, "h": 120, "label": "fuel tank", "value": 0.5},
    {"id": "P", "type": "pipe", "d": "M320 180 H470", "value": 0},
    {"id": "V", "type": "valve", "x": 400, "y": 180, "label": "master valve", "value": 1}],
    "steps": [{"title": "The valve closes", "play": [["V", 0, 600]]}]}
GOOD["parts"].append({"type": "text", "x": 190, "y": 186, "text": "words printed on the tank's own outline", "fixed": True})
BAD = json.loads(json.dumps(GOOD))
GOOD["parts"].pop()

# ---------------------------------------------------------------- 2.49.1: what IGF M06 found in the kit (K1-K13, C11)
# each spec below failed (or lacked the part) in the kit as it was at 2.49.0
SPECS = {
    # K2: tick numbers did not grow with the 12.5 px text growth -> over the bar at 1024 x 768
    "ticks": {"size": [800, 330], "label": "scales with ticks", "parts": [
        {"id": "S", "type": "scale", "x": 40, "y": 60, "orient": "h", "len": 700, "w": 18, "min": 0, "max": 50, "every": 10, "unit": "ppm"},
        {"id": "V", "type": "scale", "x": 40, "y": 180, "h": 130, "w": 18, "min": 0, "max": 2500, "every": 500, "unit": "ppm",
         "reach": 200, "limits": [{"at": 1500, "label": "limit"}]}],
        "steps": [{"title": "x", "play": [["S", 0.5, 500]]}]},
    # K1: marker words and notes are labels the layout places - two markers 50 ppm apart no longer print over each other
    "close": {"size": [640, 330], "label": "two close markers", "parts": [
        {"id": "S", "type": "scale", "x": 50, "y": 300, "orient": "h", "len": 540, "w": 18, "min": 0, "max": 2500, "every": 500, "unit": "ppm",
         "markers": [{"label": "TWA 200 ppm", "note": "8-hour average", "at": 200, "rise": 170},
                     {"label": "STEL 250 ppm", "note": "up to 15 minutes", "at": 250, "rise": 170}]}],
        "steps": [{"title": "a", "play": [["S", 1, 800]]}, {"title": "b", "play": [["S", 2, 800]]}]},
    # K7: a flame burns over a tank and a room by its nature. K8: a box laid over a tank's end is meant to cross it; the
    # name of a narrow room goes outside it instead of poking out of its side
    "fire_space": {"size": [640, 330], "label": "flames and boxes over a tank", "parts": [
        {"id": "T", "type": "tank", "x": 30, "y": 120, "w": 300, "h": 130, "label": "fuel tank", "value": 0.6},
        {"id": "R", "type": "space", "x": 250, "y": 130, "w": 150, "h": 110, "label": "CONNECTION SPACE", "crosses": True},
        {"id": "S", "type": "space", "x": 470, "y": 130, "w": 70, "h": 60, "label": "FUEL PREPARATION ROOM"},
        {"id": "F", "type": "flame", "x": 150, "y": 120, "size": 90, "label": "burning at the tank top"},
        {"id": "G", "type": "flame", "x": 330, "y": 190, "size": 60}],
        "steps": [{"title": "lit", "play": [["R", 1, 600], ["S", 1, 600], ["F", 1, 600], ["G", 1, 600]]}]},
    # K6: the static_charge's own words stood on its hose line at every size
    "static": {"size": [640, 390], "label": "static charge, not bonded and bonded (IGF M06 s05, with its words and callouts)", "parts": [
        {"id": "A", "type": "static_charge", "x": 165, "y": 130, "label": "not bonded"},
        {"id": "B", "type": "static_charge", "x": 475, "y": 130, "bonded": True, "label": "bonded to earth"},
        {"type": "text", "x": 250, "y": 100, "text": "fuel flowing fast", "to": [169, 160]},
        {"type": "text", "x": 80, "y": 335, "text": "isolated metal part", "to": [150, 250]},
        {"type": "text", "x": 300, "y": 345, "text": "a few millijoules light the gas", "to": [245, 230]},
        {"type": "text", "x": 380, "y": 40, "text": "LNG conducts poorly -\nit holds its charge", "to": [195, 185]},
        {"type": "text", "x": 470, "y": 374, "text": "bonded to the hull", "to": [383, 265]}],
        "steps": [{"title": "charge", "play": [["A", 1, 2600, 0, "linear"]]}, {"title": "spark", "play": [["A", 1.1, 600]]},
                  {"title": "bonded", "play": [["A", 1.25, 300], ["B", 1, 2600, 0, "linear"]]}]},
    # K3: "0" crowded a lower limit of 4 - 6 %; K3b the "nums" option
    "range": {"size": [640, 330], "label": "ranges", "parts": [
        {"id": "M", "type": "range_bar", "x": 40, "y": 110, "w": 240, "lel": 4, "uel": 75, "label": "hydrogen in air", "value": 0},
        {"id": "H", "type": "range_bar", "x": 340, "y": 110, "w": 260, "lel": 5, "uel": 15, "nums": [5, 15, 100], "label": "methane in air", "value": 0}],
        "steps": [{"title": "lean", "play": [["M", 2, 800], ["H", 2, 800]]}, {"title": "burns", "play": [["M", 10, 800], ["H", 10, 800]]}]},
    # 2.49.2 (IGF M07-M15, F8): two push buttons stack in a 390-high figure; a tree of four columns in a 640-wide figure keeps its
    # words at 12.5 px; a level fed by a pipe from the left keeps its tick numbers off it; a spill stays in its box; a long alarm
    # fits a narrow log
    "stack": {"size": [640, 390], "label": "two ESD buttons one above the other", "parts": [
        {"id": "A", "type": "push_button", "x": 100, "y": 90, "tag": "ESD 1", "label": "bunkering ESD"},
        {"id": "B", "type": "push_button", "x": 100, "y": 270, "tag": "ESD 2", "label": "fuel supply stop"},
        {"id": "C", "type": "push_button", "x": 400, "y": 120, "h": 182, "tag": "ESD 3", "label": "full size"},
        {"id": "L", "type": "log", "x": 330, "y": 280, "w": 290, "rows": 1}],
        "steps": [{"title": "both pressed", "play": [["A", 1, 800], ["B", 1, 800], ["C", 1, 800]]}]},
    "tree": {"size": [640, 390], "label": "emergency organisation", "parts": [
        {"id": "T", "type": "tree", "x": 10, "y": 10, "root": "Master", "value": 0,
         "children": [{"label": "Chief officer\n(on-scene leader)", "children": ["Deck team", "Fire team", "Medical"]},
                      {"label": "Chief engineer\n(engine control)", "children": ["Engine team", "Fuel shutdown"]},
                      {"label": "Second officer\n(communications)", "children": ["Radio"]},
                      {"label": "Bosun", "children": ["Boundary cooling"]}]}],
        "steps": [{"title": "The master commands", "play": [["T", 1, 500]]}, {"title": "The deck team", "play": [["T", 5, 500]]}]},
    "level_feed": {"size": [520, 330], "label": "a tank level column fed from the left", "parts": [
        {"id": "L", "type": "level", "x": 330, "y": 50, "w": 60, "h": 200, "label": "TANK LEVEL", "min": 0, "max": 100, "unit": "%", "value": 20,
         "marks": [{"at": 90, "kind": "alarm", "label": "HIGH"}]},
        {"id": "P", "type": "pipe", "d": "M60 200 H330", "value": 0},
        {"id": "V", "type": "valve", "x": 170, "y": 200, "label": "fill valve", "value": 1}],
        "steps": [{"title": "The tank fills", "play": [["L", 85, 800], ["P.fill", 1, 300]]}]},
    "spill_box": {"size": [640, 270], "label": "spills on deck and on water", "parts": [
        {"id": "SD", "type": "spill", "x": 40, "y": 10, "w": 200, "surface": "deck", "label": "on the deck", "value": 0},
        {"id": "SW", "type": "spill", "x": 400, "y": 10, "w": 200, "surface": "water", "label": "on the water", "reach": 999, "value": 0}],
        "steps": [{"title": "spreading", "play": [["SD", 1, 800], ["SW", 1, 800]]}]},
    "long_log": {"size": [640, 330], "label": "a narrow alarm log with long alarm text", "parts": [
        {"id": "L", "type": "level", "x": 60, "y": 40, "h": 200, "unit": "%", "min": 0, "max": 100, "value": 0, "label": "TANK",
         "marks": [{"at": 40, "kind": "alarm", "alarm": "Very high level - ESD of ship and shore, fuel supply stopped"},
                   {"at": 70, "kind": "trip", "alarm": "Gas 40 % LEL - ESD"}]},
        {"id": "G", "type": "log", "x": 330, "y": 60, "w": 250, "rows": 2}],
        "steps": [{"title": "alarm", "play": [["L", 50, 600]]}, {"title": "trip", "play": [["L", 80, 600]]}]},
}
# 2.50.4 (M01 benchmark run 4, issue 5): IGF M01 s04's GA, shared by q01 / q03 / m01. q01's answers are the four spaces; with
# their words taken out of the spec the kit re-laid the rest and put "Fuel tank" under the tank connection space
GA_M01 = {"size": [640, 230], "label": "IGF M01 s04", "parts": [
    {"id": "GA", "type": "ga", "view": "side", "x": 10, "y": 100, "w": 620, "h": 110, "house": {"x": 30, "w": 110, "h": 50}, "funnel": {"x": 60, "w": 30, "h": 24}},
    {"id": "ER", "type": "space", "x": 150, "y": 110, "w": 120, "h": 80, "label": "Engine room", "style": "room"},
    {"id": "FPR", "type": "space", "x": 276, "y": 110, "w": 70, "h": 60, "label": "Fuel preparation room", "style": "room"},
    {"id": "TCS", "type": "space", "x": 352, "y": 110, "w": 56, "h": 70, "label": "Tank connection space", "style": "enclosure"},
    {"id": "TK", "type": "tank", "x": 414, "y": 115, "w": 160, "h": 70, "label": "Fuel tank", "value": 0.6},
    {"id": "BS", "type": "space", "x": 440, "y": 70, "w": 80, "h": 26, "label": "Bunkering station", "style": "room"},
    {"id": "VP", "type": "pipe", "fluid": "gas", "d": "M596 100 V36", "value": 0},
    {"id": "VM", "type": "vent", "x": 596, "y": 36, "labelAt": "left", "label": "Vent mast"}]}
GA_ANSWERS = ["TCS", "FPR", "BS", "ER"]
# a task figure is still (it keeps its frame); each label where the layout left it, and whether it is shown
GA_JS = ("svg.setAttribute('data-kit-still','');f.layout(true);var o={};[].forEach.call(svg.querySelectorAll('.kit-lbl'),function(l){"
         "var L=l.__kitL;if(L.at)o[l.textContent]={at:[L.at.x,L.at.y].map(Math.round),shown:getComputedStyle(l).display!=='none'};});return o;")

# for kit_eval: what a part does in the page, read back as numbers and words
EVALS = {
    # K5: words a step brings in; K11: a wrapped alarm keeps its space; K4: the new tank/cloud values; K10: no pipe stub
    "reveal": ({"size": [640, 300], "label": "reveal", "parts": [
        {"id": "T", "type": "text", "x": 320, "y": 40, "text": "the answer", "reveal": True},
        {"id": "C", "type": "text", "x": 200, "y": 70, "text": "vapour space", "to": [100, 190], "reveal": True},
        {"id": "P", "type": "text", "x": 500, "y": 40, "text": "always there"},
        {"id": "K", "type": "tank", "x": 60, "y": 150, "w": 200, "h": 100, "value": 0.5}],
        "steps": [{"title": "show", "play": [["T", 1, 300], ["C", 1, 300]]}]},
        "var g=function(i){return svg.querySelector('[data-kit-id=\"'+i+'\"]');};f.layout(true);f.go(0,true);"
        "var lv=function(){return [].map.call(svg.querySelectorAll('.kit-leaders line'),function(l){return l.style.opacity;});};"
        "var a={T:g('T').style.opacity,C:g('C').style.opacity,P:g('P').style.opacity,L:lv()};f.go(1,true);"
        "return {a:a,b:{T:g('T').style.opacity,C:g('C').style.opacity,L:lv()}};"),
    "log": ({"size": [640, 240], "label": "log", "parts": [
        {"id": "L", "type": "level", "x": 40, "y": 40, "h": 150, "marks": [{"at": 50, "kind": "alarm", "alarm": "HIGH PRESSURE ALARM"}]},
        {"id": "G", "type": "log", "x": 300, "y": 60, "w": 220, "rows": 1}],
        "steps": [{"title": "alarm", "play": [["L", 60, 600]]}]},
        "f.layout(true);f.go(1,true);return [].map.call(svg.querySelectorAll('text.kit-msg'),function(t){return t.textContent;});"),
    "burst": ({"size": [520, 300], "label": "burst", "parts": [
        {"id": "T", "type": "tank", "x": 120, "y": 90, "w": 240, "h": 120, "burst": {"r": 110, "label": "tank ruptures"}, "value": 0.7},
        {"id": "C", "type": "gas_cloud", "x": 20, "y": 20, "w": 200, "h": 100, "from": [60, 70], "drift": [80, 0]}],
        "steps": [{"title": "burst", "play": [["T.burst", 1, 800]]}, {"title": "drift", "play": [["C", 1, 500], ["C.drift", 1, 800]]}]},
        "var q=function(s){return svg.querySelector(s);};f.layout(true);f.go(0,true);"
        "var nm=function(){return [].filter.call(svg.querySelectorAll('[data-kit-id=\"T\"] .kit-lbl'),function(x){return /ruptures/.test(x.textContent);})[0].style.opacity;};"
        "var a={ball:q('.kit-tank-fireball').style.opacity,hot:q('[data-kit-id=\"T\"]').classList.contains('kit-tank-burst'),name:nm()};"
        "f.go(1,true);var b={ball:q('.kit-tank-fireball').style.opacity,tf:q('.kit-tank-fireball').getAttribute('transform'),"
        "hot:q('[data-kit-id=\"T\"]').classList.contains('kit-tank-burst'),name:nm()};f.go(2,true);"
        "return {a:a,b:b,drift:q('[data-kit-id=\"C\"] > g').getAttribute('transform')};"),
    "stub": ({"size": [400, 200], "label": "stub", "parts": [
        {"id": "A", "type": "fire", "kind": "jet", "x": 100, "y": 100, "length": 200, "value": 1},
        {"id": "B", "type": "fire", "kind": "jet", "x": 100, "y": 170, "length": 200, "value": 1, "stub": False}]},
        "return [svg.querySelectorAll('[data-kit-id=\"A\"] .kit-pipe').length,svg.querySelectorAll('[data-kit-id=\"B\"] .kit-pipe').length];"),
    "bar": ({"size": [520, 220], "label": "composition", "parts": [
        {"id": "C", "type": "composition_bar", "x": 30, "y": 90, "w": 460, "label": "natural gas",
         "segments": [{"label": "methane", "pct": 90}, {"label": "ethane", "pct": 6}, {"label": "nitrogen", "pct": 4}]}],
        "steps": [{"title": "two", "play": [["C", 2, 500]]}]},
        "f.layout(true);f.go(1,true);var r=[].map.call(svg.querySelectorAll('.kit-composition-bar-s'),function(x){return +x.getAttribute('width');});"
        "var l=[].map.call(svg.querySelectorAll('.kit-lbl'),function(x){return x.style.opacity;});return {w:r,l:l};"),
    # a value set from outside the steps (a task page's panel valve turned to "closed") survives a layout (a font arriving, a resize)
    "keep": ({"size": [200, 100], "label": "valve", "parts": [{"id": "c", "type": "valve", "x": 100, "y": 50, "size": 22, "state": False, "value": 1}]},
             "f.set(f.parts.c,0);f.layout(true);return [f.parts.c.v,svg.querySelectorAll('g.kit-shut').length];"),
    "drip": ({"size": [420, 240], "label": "drip", "parts": [
        {"id": "D", "type": "drip_tray", "x": 110, "y": 80, "w": 200, "label": "drip tray", "labelAt": "right"}]},
        "f.layout(true);var t=svg.querySelector('[data-kit-id=\"D\"] .kit-lbl text');return +t.getAttribute('x');"),
    # F3: gas_cloud "from" in figure coordinates (and in the cloud's own box, as older specs wrote it): the cloud grows from the same place
    "cloud_from": ({"size": [640, 390], "label": "clouds", "parts": [
        {"id": "A", "type": "gas_cloud", "x": 350, "y": 110, "w": 250, "h": 120, "from": [450, 190]},
        {"id": "B", "type": "gas_cloud", "x": 20, "y": 110, "w": 250, "h": 120, "from": [100, 80]},
        {"id": "C", "type": "gas_cloud", "x": 20, "y": 250, "w": 280, "h": 120, "from": [110, 270], "fromIn": "figure"},
        {"id": "D", "type": "gas_cloud", "x": 350, "y": 250, "w": 250, "h": 120}],
        "steps": [{"title": "gas", "play": [["A", 1, 300], ["B", 1, 300], ["C", 1, 300], ["D", 1, 300]]}]},
        "f.layout(true);f.go(1,true);var o={};['A','B','C','D'].forEach(function(i){var g=svg.querySelector('[data-kit-id=\"'+i+'\"] g[filter]');"
        "var m=/translate\\(([-\\d.]+) ([-\\d.]+)\\) scale/.exec(g.getAttribute('transform'));o[i]=m?[+m[1],+m[2]]:g.getAttribute('transform');});return o;"),
    # F8: push_button 120 units by default (182 before), "h" sizes it; level ticks on the right when a pipe comes in on the left
    "push_h": ({"size": [640, 390], "label": "buttons", "parts": [
        {"id": "A", "type": "push_button", "x": 100, "y": 110, "tag": "ESD 1"},
        {"id": "B", "type": "push_button", "x": 300, "y": 110, "tag": "ESD 2", "h": 182},
        {"id": "L", "type": "level", "x": 500, "y": 40, "h": 150},
        {"id": "M", "type": "level", "x": 400, "y": 240, "h": 100, "ticks": "right"},
        {"id": "N", "type": "level", "x": 200, "y": 240, "h": 100},
        {"id": "P", "type": "pipe", "d": "M440 90 H500", "value": 0}],
        "steps": [{"title": "go", "play": [["A", 1, 300]]}]},
        "f.layout(true);var pl=function(i){return svg.querySelector('[data-kit-id=\"'+i+'\"] .kit-push-button-plate').getBBox().height;};"
        "var an=function(i){return [].map.call(svg.querySelectorAll('[data-kit-id=\"'+i+'\"] text.kit-tick'),function(t){return t.getAttribute('text-anchor');});};"
        "return {a:pl('A'),b:pl('B'),lev:an('L'),lev2:an('M'),lev3:an('N')};"),
    # F8: a spill stays in its box (x..x+w, y..y+h), with a reach that asks for more than the room and a water wave that is not a whole number of 30s
    "spill_in": ({"size": [640, 330], "label": "spill", "parts": [
        {"id": "S", "type": "spill", "x": 40, "y": 20, "w": 200, "surface": "water", "label": "on the water", "reach": 999, "value": 0},
        {"id": "T", "type": "spill", "x": 340, "y": 20, "w": 230, "h": 170, "surface": "deck", "value": 0}],
        "steps": [{"title": "boil", "play": [["S", 1, 300], ["T", 1, 300]]}]},
        "f.layout(true);f.go(1,true);var b=function(i){var r=svg.querySelector('[data-kit-id=\"'+i+'\"]'),p=r.querySelectorAll('rect,path,circle,line');"
        "var x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;[].forEach.call(p,function(e){var q=e.getBBox();if(e.classList.contains('kit-spill-wisp')||e.classList.contains('kit-spill-bub'))return;"
        "x0=Math.min(x0,q.x);y0=Math.min(y0,q.y);x1=Math.max(x1,q.x+q.width);y1=Math.max(y1,q.y+q.height);});return [Math.round(x0),Math.round(y0),Math.round(x1),Math.round(y1)];};"
        "var w=function(i){var q=svg.querySelector('[data-kit-id=\"'+i+'\"] .kit-spill-pool').getBBox();return [Math.round(q.x),Math.round(q.x+q.width)];};"
        "return {s:b('S'),t:b('T'),pool:w('S')};"),
    # F22: the names of a person's items - the defaults, and the slide's own words per item (object or list); goggles, respirator, apron are drawn
    "person_words": ({"size": [640, 330], "label": "ppe", "parts": [
        {"id": "A", "type": "person", "x": 110, "y": 290, "scale": 1.3, "wear": ["goggles", "respirator", "apron", "gloves"], "labels": {"respirator": "HALF MASK"}},
        {"id": "B", "type": "person", "x": 320, "y": 290, "scale": 1.3, "wear": ["helmet", "visor", "scba"], "labels": ["HARD HAT", "GOGGLES"]},
        {"id": "C", "type": "person", "x": 530, "y": 290, "scale": 1.3, "wear": ["visor", "suit"], "labels": False}],
        "steps": [{"title": "on", "play": [["A", 4, 300], ["B", 3, 300], ["C", 2, 300]]}]},
        "f.layout(true);f.go(1,true);var t=function(i){return [].map.call(svg.querySelectorAll('[data-kit-id=\"'+i+'\"] .kit-lbl text'),function(x){return x.textContent;});};"
        "return {a:t('A'),b:t('B'),c:t('C')};"),
    # F4: a drawing shown below 1:1 (a photo over it keeps it from being zoomed to fill its panel) has every word at 12.5 px or more
    # by the deck audit's own sum (declared x rendered width / viewBox width), not 12.4999; and a window resize lays it out
    "floor": ({"size": [640, 390], "label": "floor", "parts": [
        {"id": "G", "type": "level", "x": 40, "y": 60, "h": 200, "unit": "%", "min": 0, "max": 100, "label": "TANK", "value": 40,
         "marks": [{"at": 80, "kind": "alarm", "label": "HIGH"}]},
        {"id": "T", "type": "tank", "x": 200, "y": 120, "w": 280, "h": 120, "label": "fuel tank", "value": 0.5}]},
        "var small=function(){var vb=svg.getAttribute('viewBox').split(/[ ,]+/).map(Number),sc=svg.getBoundingClientRect().width/vb[2],m=1e9;"
        "[].forEach.call(svg.querySelectorAll('text'),function(t){var f=parseFloat(getComputedStyle(t).fontSize);if(f)m=Math.min(m,f*sc);});return m;};"
        "f.layout(true);var a=small();f.laid=0;svg.style.removeProperty('--kit-up');svg.setAttribute('viewBox','0 0 640 390');"
        "window.dispatchEvent(new Event('resize'));return {min:a,laid:f.laid>0,up:svg.style.getPropertyValue('--kit-up'),after:small()};", 380),
    # 2.50.4 (M01 benchmark run 4, issue 3): "mast": true with no pipe under the vent drew a bare outlet in the air. Now a true
    # or a length with no pipe under it is drawn; a pipe's own upright run is never drawn twice; false is the outlet alone
    "vent_mast": ({"size": [640, 300], "label": "vent masts", "parts": [
        {"id": "A", "type": "vent", "x": 80, "y": 40, "mast": True},
        {"id": "B", "type": "vent", "x": 220, "y": 40, "mast": 120},
        {"id": "P", "type": "pipe", "d": "M360 240 V40", "value": 0},
        {"id": "C", "type": "vent", "x": 360, "y": 40, "mast": True},
        {"id": "D", "type": "vent", "x": 500, "y": 40, "mast": False}]},
        "var q=function(i,s){return svg.querySelector('[data-kit-id=\"'+i+'\"] '+s);};"
        "var h=function(i){var m=q(i,'.kit-vent-mast');return m?Math.round(m.getBBox().height):0;};"
        "var hit=function(i){var r=q(i,'.kit-hit');return r?Math.round(+r.getAttribute('height')):0;};"
        "return {drawn:[h('A'),h('B'),h('C'),h('D')],hit:[hit('A'),hit('B'),hit('C'),hit('D')]};"),
    # 2.50.4 (M01 benchmark run 4, issue 4): a cylinder's own labels name its features (oil injector, gas injector, exhaust
    # valve, piston). A tank on its left and a room on its right push two of them away - each must keep a leader to its
    # feature, or stay beside it; before, the oil injector's words went 37 units up the cylinder's side with no line
    "cyl_leaders": ({"size": [640, 330], "label": "a cylinder between a tank and a room", "parts": [
        {"id": "CY", "type": "cylinder", "x": 230, "y": 50, "w": 140, "h": 230},
        {"id": "T", "type": "tank", "x": 20, "y": 40, "w": 180, "h": 90, "label": "fuel tank", "value": 0.5},
        {"id": "R", "type": "space", "x": 400, "y": 20, "w": 220, "h": 120, "label": "ENGINE ROOM"}]},
        "f.layout(true);var inv=svg.getScreenCTM().inverse(),out=[];"
        "[].forEach.call(svg.querySelectorAll('[data-kit-id=\"CY\"] .kit-lbl'),function(l){var L=l.__kitL,a=L.opt.at;if(!a||!L.at)return;"
        "var M=inv.multiply(l.parentNode.getScreenCTM()),px=M.a*a[0]+M.c*a[1]+M.e,py=M.b*a[0]+M.d*a[1]+M.f;"
        "var dx=Math.max(0,L.at.x-px,px-L.at.x2),dy=Math.max(0,L.at.y-py,py-L.at.y2);"
        "out.push({t:l.textContent,moved:Math.round(Math.hypot(L.at.x-L.box.x,L.at.y-L.box.y)),gap:Math.round(Math.hypot(dx,dy)),"
        "leader:!!l.__kitLeader});});return out;"),
}


def kit_eval(spec, js, width=640):
    """the spec drawn by the factory's kit.js in a page `width` px wide; `js` (a function body, with f = the figure and svg)
    runs once it is up and returns what it found, as JSON"""
    exe = studio.find_browser()
    tmp = tempfile.mkdtemp(prefix="kit_eval_")
    try:
        css = "".join('<link rel="stylesheet" href="%s">' % studio.uri(os.path.join(d, n)) for d, n in
                      ((studio.TOKENS, "gb_tokens.css"), (studio.KIT, "kit.css")) if os.path.isfile(os.path.join(d, n)))
        run = ("<script>setTimeout(function(){var svg=document.querySelector('svg[data-kit]'),f=svg.__kit,o;"
               "try{o=(function(f,svg){%s})(f,svg);}catch(e){o={error:String(e)};}"
               "var p=document.createElement('pre');p.id='o';p.textContent=JSON.stringify(o);document.body.appendChild(p);},500);</script>" % js)
        page = os.path.join(tmp, "eval.html")
        io.open(page, "w", encoding="utf-8").write(
            '<!DOCTYPE html><html><head><meta charset="utf-8">%s</head><body style="margin:0"><div class="kit-screen" style="width:%dpx">'
            '<svg data-kit="#s"></svg></div><script type="application/json" id="s">%s</script><script src="%s"></script>%s</body></html>'
            % (css, width, json.dumps(spec).replace("</", "<\\/"), studio.uri(os.path.join(studio.KIT, "kit.js")), run))
        ok, dom = studio.chrome(exe, studio.uri(page), (width + 40, 700), os.path.join(tmp, "p")).wait(60)
        m = re.search(r'<pre id="o">(.*?)</pre>', dom or "", re.S)
        return json.loads(html.unescape(m.group(1))) if m else None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def png_size(path):
    with io.open(path, "rb") as fh:
        head = fh.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def findings(r, drop=("empty",)):
    """every finding but the ones named, at every size - the studio judges 1280 and only states 1024; these specs are held to both"""
    return [p for p in studio.problems(r) if p[2] not in drop]


def judged_part():
    """2.49.4 - the studio never says clean about a size it did not measure (no browser needed)"""
    clean = {"states": [{"step": 0, "findings": []}], "report": {}}
    _, p = studio.summary({"sizes": {"1920x1080": clean}}, "x.kit.json")
    check("--sizes without 1280x800: not clean - the tablet size was never measured", p and p[0][2] == "not measured", p)
    _, p = studio.summary({"sizes": {"1280x800": clean}}, "x.kit.json")
    check("... with it, a figure with no findings is clean", p == [], p)
    aborted = {"states": [{"step": 0, "findings": [], "aborted": "viewport under 320 px"}], "report": {}}
    _, p = studio.summary({"sizes": {"1280x800": aborted}}, "x.kit.json")
    check("an audit that aborted is a finding, not a clean step", any(c == "aborted" for _, _, c, _, _ in p), p)


# 2.52.1 (M01 rebuild 2026-10-20, runs 1 and 3) - a ship drawing a task question stands on: clean in the studio's 640 px task
# panel, EMPTY in the real task page's frame (~1000 px wide, the words smaller beside the drawing)
SHIP = {"size": [640, 330], "label": "ship", "parts": [
    {"id": "G", "type": "ga", "x": 20, "y": 170, "w": 600, "h": 130, "house": {"x": 40, "w": 90, "h": 50},
     "funnel": {"x": 60, "w": 22, "h": 24}, "label": "LNG-fuelled ship"},
    {"id": "TCS", "type": "space", "x": 200, "y": 178, "w": 120, "h": 110, "label": "Tank connection space"},
    {"id": "ER", "type": "space", "x": 340, "y": 178, "w": 120, "h": 110, "label": "Engine room"},
    {"id": "T", "type": "tank", "x": 60, "y": 190, "w": 120, "h": 80, "label": "Fuel tank", "value": 0.5},
    {"id": "VP", "type": "pipe", "fluid": "gas", "d": "M520 170 V50", "value": 0},
    {"id": "VO", "type": "vent", "x": 520, "y": 50, "label": "Vent mast", "labelAt": "right"},
    {"id": "BS", "type": "space", "x": 200, "y": 120, "w": 120, "h": 40, "style": "enclosure", "label": "Bunkering station"}]}


def task_page_part():
    """2.52.1 - --panel task on a spec a course's task question stands on draws the REAL task page (task_pages.page_html), so
    the studio judges what the build's drawing check judges; a spec outside a course keeps the generic 640 px panel"""
    print("\n-- --panel task: the real task page (2.52.1)")
    sys.path.insert(0, studio.COMPILE)
    import test_compile_module as tcm
    import figure_fit as ff
    import content_script as cs
    import task_pages
    tmp = tempfile.mkdtemp(prefix="studio_task_")
    try:
        screens = [{"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the ship", "text": "Self-check now.", "minutes": 2},
                   {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the tank connection space.",
                    "visual": "the ship", "answer": "Tank connection space*\nEngine room", "feedback": "Around the valves."}]
        build = {"module": 1, "screens": {"t01": {"try_tablet": False},
                                          "q01": {"figure": "ship.kit.json", "areas": {"Tank connection space": "TCS", "Engine room": "ER"}}}}
        c, md = tcm.figures_course(tmp, build=build, screens=screens)
        figdir = os.path.join(c, "working_claude", "figures", "M01")
        sp = os.path.join(figdir, "ship.kit.json")
        io.open(sp, "w", encoding="utf-8").write(json.dumps(SHIP))
        loose = os.path.join(tmp, "ship.kit.json")
        io.open(loose, "w", encoding="utf-8").write(json.dumps(SHIP))
        rg, _ = studio.run(loose, panel="task", sizes=((1280, 800),), out=os.path.join(tmp, "g"))
        check("outside a course: the generic 640 px task panel, where this ship is clean (the case it fixes)",
              rg and not (rg.get("context") or {}).get("page") and not [p for p in studio.problems(rg) if p[2] == "empty"],
              rg and studio.problems(rg))
        script = cs.load(cs.paths(c, 1)["script"])
        slide, code, qs = next(iter(task_pages.sets(script)))
        real = ff.task_page_findings(studio.find_browser(), script, slide, code, qs, build, md, figdir) or {}
        r, _ = studio.run(sp, panel="task", out=os.path.join(tmp, "t"))
        st = (((r or {}).get("sizes") or {}).get("1280x800") or {}).get("states") or [{}]
        text, probs = studio.summary(r, sp) if r else ("", [])
        check("in a course: drawn on q01's real task page (its frame ~1000 px wide, not 640), and the studio finds what the "
              "build's drawing check finds there - EMPTY",
              r and (r.get("context") or {}).get("page") and (st[-1].get("panel") or [0])[0] > 900
              and any(x[0] == "empty" for x in real.get("q01", [])) and any(p[2] == "empty" for p in probs)
              and "its real task page" in text, (st, real.get("q01"), text[-600:]))
        shot = (((r or {}).get("sizes") or {}).get("1280x800") or {}).get("shot") or ""
        check("... and photographs that page (the question shown)", shot.endswith("_task_1280x800.png") and os.path.isfile(shot), shot)
        check("... the temporary pages are gone from the module folder",
              not [f for f in os.listdir(os.path.join(md, "tasks")) if f.startswith("__studio_")]
              if os.path.isdir(os.path.join(md, "tasks")) else True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    judged_part()
    if not studio.find_browser():
        print("SKIP - no Chrome or Edge (set CF_BROWSER)")
        return 0
    tmp = tempfile.mkdtemp(prefix="kit_studio_test_")
    try:
        good, bad = os.path.join(tmp, "good.kit.json"), os.path.join(tmp, "bad.kit.json")
        io.open(good, "w", encoding="utf-8").write(json.dumps(GOOD))
        io.open(bad, "w", encoding="utf-8").write(json.dumps(BAD))
        r, why = studio.run(good, panel="two-col", out=os.path.join(tmp, "shots"))
        check("the studio runs", r is not None, why)
        if r:
            text, probs = studio.summary(r, good)
            check("a well-made figure is clean at 1280 x 800, every step", not probs, text)
            big = r["sizes"].get("1280x800", {})
            check("both sizes are drawn", set(r["sizes"]) == {"1280x800", "1024x768"}, sorted(r["sizes"]))
            check("each step is audited (2 states)", len(big.get("states", [])) == 2, big.get("states"))
            rep = big.get("report") or {}
            check("the layout reports what it did", {"scale", "up", "labels", "moved", "unplaced", "theme"} <= set(rep), rep)
            check("on a deck's dark panel the figure is dark", rep.get("theme") == "dark", rep.get("theme"))
            check("no word under 12.5 px", (rep.get("minTextPx") or 0) >= 12.45, rep.get("minTextPx"))
            check("a screenshot per size", all(os.path.isfile(v.get("shot") or "") for v in r["sizes"].values()),
                  [v.get("shot") for v in r["sizes"].values()])
        r2, _ = studio.run(good, panel="task", sizes=((1280, 800),), out=os.path.join(tmp, "shots2"))
        check("on a task page the figure is the deck's dark screen too (2.46.0 gb_answer.css) - the kit sees it", r2 and
              (r2["sizes"]["1280x800"].get("report") or {}).get("theme") == "dark")
        light = os.path.join(tmp, "light.kit.json")
        io.open(light, "w", encoding="utf-8").write(json.dumps(dict(GOOD, theme="light")))
        r4, _ = studio.run(light, panel="task", sizes=((1280, 800),), out=os.path.join(tmp, "shots4"))
        _, p4 = studio.summary(r4, light) if r4 else (None, ["no run"])
        check("\"theme\": \"light\" takes the light colours, and it is clean on them (contrast by construction)", r4 and
              (r4["sizes"]["1280x800"].get("report") or {}).get("theme") == "light" and not p4, p4)
        r3, _ = studio.run(bad, panel="two-col", sizes=((1280, 800),), out=os.path.join(tmp, "shots3"))
        _, p3 = studio.summary(r3, bad) if r3 else (None, [])
        check("words fixed on a line are found (text zone)", any(c == "text zone" for _, _, c, _, _ in p3), p3)

        # ------------------------------------------------------------ 2.49.1 - IGF M06's kit and checker problems
        runs = {}
        for name, spec in SPECS.items():
            f = os.path.join(tmp, name + ".kit.json")
            io.open(f, "w", encoding="utf-8").write(json.dumps(spec))
            runs[name] = studio.run(f, panel="two-col", out=os.path.join(tmp, "shots_" + name))[0]
            check("%s: the studio runs" % name, runs[name] is not None)
        rep = lambda name, size="1280x800": (runs[name]["sizes"].get(size) or {}).get("report") or {}
        if all(runs.values()):
            check("K2 scale ticks: numbers keep clear of the bar and their ticks as the type grows (1280 and 1024)",
                  not findings(runs["ticks"]), findings(runs["ticks"]))
            check("K1 scale markers: words, notes and a limit's name are labels the layout places (1 limit + 2 markers = 3, 2 markers = 2)",
                  rep("ticks")["labels"] == 1 and rep("close")["labels"] == 2, (rep("ticks"), rep("close")))
            check("K1 two markers 50 ppm apart: their words are moved clear of each other, at both sizes",
                  not findings(runs["close"]) and rep("close")["moved"] >= 1, (findings(runs["close"]), rep("close")))
            check("K7 + K8: a flame over a tank and a room, a box over a tank's end (crosses), the name of a narrow room: clean at both sizes",
                  not findings(runs["fire_space"]), findings(runs["fire_space"]))
            check("K6 static_charge: its label and state stand above the hose line, at both sizes",
                  not [p for p in findings(runs["static"]) if "pipe" in p[3] or "kit-pipe" in p[4]],
                  findings(runs["static"]))
            check("K3 range_bar: no \"0\" crowding a lower limit of 4 or 5 %, and \"nums\" names the numbers (1280 and 1024)",
                  not [p for p in findings(runs["range"]) if "kit-tick" in p[3]], findings(runs["range"]))

        v = kit_eval(*EVALS["reveal"])
        check("K5 text with \"reveal\" is not drawn at rest, and fades in with its value; a plain text always stands",
              v and v["a"]["T"] == "0" and v["a"]["C"] == "0" and v["a"]["P"] == "" and v["b"]["T"] == "1" and v["b"]["C"] == "1", v)
        check("K5 a revealed callout's leader line is hidden at rest and shown with it",
              v and v["a"]["L"] and set(v["a"]["L"]) == {"0"} and set(v["b"]["L"]) == {"1"}, v)
        v = kit_eval(*EVALS["log"])
        check("K11 a wrapped alarm keeps its space (\"HIGH PRESSURE ALARM\", not \"HIGH PRESSUREALARM\")",
              v and any(m == "HIGH PRESSURE ALARM" for m in v), v)
        v = kit_eval(*EVALS["burst"])
        check("K4 tank \"burst\": no fireball at rest, a fireball and a red shell once \"<id>.burst\" has played",
              v and v["a"]["ball"] == "0" and not v["a"]["hot"] and v["b"]["ball"] == "1" and v["b"]["hot"]
              and "scale(1.000)" in v["b"]["tf"] and v["a"]["name"] == "0" and v["b"]["name"] == "1", v)
        check("K4 gas_cloud \"drift\": \"<id>.drift\" carries the cloud its distance", v and v["drift"] == "translate(80.0 0.0)", v)
        v = kit_eval(*EVALS["stub"])
        check("K10 a jet fire draws its pipe stub unless \"stub\": false", v == [1, 0], v)
        v = kit_eval(*EVALS["bar"])
        check("K4 composition_bar: segment k fills while the value goes k to k+1, its name shows once it is half drawn",
              v and v["w"][0] > 300 and v["w"][1] > 20 and v["w"][2] == 0 and v["l"][:3] == ["1", "1", "0"], v)
        v = kit_eval(*EVALS["keep"])
        check("a value set from outside the steps survives a layout (the task page's panel valve stayed closed only by luck)", v == [0, 1], v)
        v = kit_eval(*EVALS["drip"])
        check("K9 drip_tray: \"labelAt\" puts the name beside the pan", v is not None and v > 200, v)

        # ------------------------------------------------------------ 2.49.2 - IGF M07-M15's kit problems
        if all(runs.values()):
            check("F8 push_button: two stacked in a 390-high figure, a full-size one beside them, and a log: clean at both sizes",
                  not findings(runs["stack"]), findings(runs["stack"]))
            check("F8 tree: four columns in a 640-wide figure keep every word at 12.5 px, at both sizes (it drew 11.5)",
                  not findings(runs["tree"]) and all((runs["tree"]["sizes"][s].get("report") or {}).get("minTextPx", 0) >= 12.49
                                                      for s in runs["tree"]["sizes"]),
                  (findings(runs["tree"]), [(runs["tree"]["sizes"][s].get("report") or {}).get("minTextPx") for s in runs["tree"]["sizes"]]))
            check("F8 level: a pipe running in on the left keeps clear of the tick numbers (text zone), at both sizes",
                  not findings(runs["level_feed"]), findings(runs["level_feed"]))
            check("F8 spill: both surfaces are clean in a figure the size of their boxes, at both sizes",
                  not findings(runs["spill_box"]), findings(runs["spill_box"]))
            check("F8 log: a long alarm in a narrow log stays inside it (3 lines where it needs them), at both sizes",
                  not findings(runs["long_log"]), findings(runs["long_log"]))

        v = kit_eval(*EVALS["cloud_from"])
        check("F3 gas_cloud: \"from\" in figure coordinates, in the cloud's own box (old specs), and \"fromIn\": \"figure\" all grow from the right place",
              v and v["A"] == [100, 80] and v["B"] == [100, 80] and v["C"] == [90, 20] and v["D"] == [125, 72], v)
        v = kit_eval(*EVALS["push_h"])
        check("F8 push_button: the wall plate is 120 units by default (182 before) and \"h\" sizes it",
              v and 110 <= v["a"] <= 135 and 175 <= v["b"] <= 200, v)
        check("F8 level: tick numbers stand left of the column (end-anchored), on the right when a pipe runs in on the left or \"ticks\": \"right\"",
              v and set(v["lev"]) == {"start"} and set(v["lev2"]) == {"start"} and set(v["lev3"]) == {"end"}, v)
        v = kit_eval(*EVALS["spill_in"])
        check("F8 spill: drawn inside x..x+w (a wave cut at w, a reach held to the room), y..y+h (the box of its own words)",
              v and v["s"][0] >= -1 and v["s"][2] <= 201 and v["s"][1] >= -1 and v["s"][3] <= 245 and v["pool"][0] >= 0 and v["pool"][1] <= 200
              and v["t"][0] >= -1 and v["t"][2] <= 231 and v["t"][1] >= -1 and v["t"][3] <= 172, v)
        v = kit_eval(*EVALS["person_words"])
        check("F22 person: goggles, respirator, apron are named, and \"labels\" gives the slide's own words (an object, a list, or false for none)",
              v and v["a"] == ["GOGGLES", "HALF MASK", "APRON", "GLOVES"] and v["b"] == ["HARD HAT", "GOGGLES", "SCBA"] and v["c"] == [], v)
        v = kit_eval(*EVALS["floor"])
        check("F4 a drawing shown below 1:1 has every word at 12.5 px or more by the deck audit's own sum, not 12.4999",
              v and v["min"] >= 12.5, v)
        check("F4 a window resize lays a figure out (a probe that measures a slide at once gets no observer call)",
              v and v["laid"] and v["up"] != "" and v["after"] >= 12.5, v)
        v = kit_eval(*EVALS["vent_mast"])
        check("2.50.4 vent: \"mast\": true / a length with no pipe under it is drawn (60, 120), a pipe's run is not drawn twice, "
              "false is the outlet alone; the tap area is the whole mast",
              v and v["drawn"] == [60, 120, 0, 0] and v["hit"] == [60, 120, 200, 0], v)
        v = kit_eval(*EVALS["cyl_leaders"])
        check("2.50.4 cylinder: a label a neighbour pushes off its feature keeps a leader to it, or stays beside it (all four named; "
              "at least one pushed away with a leader)",
              v and len(v) == 4 and all(x["leader"] or x["moved"] <= 12 or x["gap"] <= 14 for x in v)
              and any(x["leader"] for x in v), v)
        full = kit_eval(GA_M01, GA_JS, 1100)
        gone = kit_eval(dict(GA_M01, ghost=GA_ANSWERS), GA_JS, 1100)
        bare = kit_eval(dict(GA_M01, parts=[dict((k, w) for k, w in p.items() if not (p["id"] in GA_ANSWERS and k == "label"))
                                            for p in GA_M01["parts"]]), GA_JS, 1100)
        check("2.50.4 ghost: the answers' words are laid out, then hidden - the words left stand exactly where the deck has them",
              full and gone and set(full) == set(gone) and all(gone[t]["at"] == full[t]["at"] for t in full)
              and [t for t in gone if gone[t]["shown"]] == ["Fuel tank", "Vent mast"], (full, gone))
        check("... the case it fixes: with the words taken out of the spec, \"Fuel tank\" moved (under the tank connection space)",
              bare and full and bare["Fuel tank"]["at"] != full["Fuel tank"]["at"], (bare, full))

        # K13: one browser run draws every step - a contact sheet, as wide as the real slide's panels
        sheet_spec = os.path.join(tmp, "sheet.kit.json")
        io.open(sheet_spec, "w", encoding="utf-8").write(json.dumps(SPECS["close"]))
        rs, _ = studio.run(sheet_spec, panel="two-col", sizes=((1280, 800),), step="all", out=os.path.join(tmp, "sheet"))
        shot = ((rs or {}).get("sizes", {}).get("1280x800") or {}).get("shot") or ""
        check("K13 --step all: one contact sheet of every step (rest + 2 steps = 3 panels) in one picture",
              shot.endswith("_all.png") and os.path.isfile(shot) and png_size(shot)[0] >= 1300 and png_size(shot)[1] >= 700, shot)
        floor_parts_part(tmp)
        probe_cache_part(tmp)
        flammability_part(tmp)
        kit_words_part()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    task_page_part()
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


# IGF M07 s02 and M11 s04 as built: a part's own words (a scale's numbers, a step's digit) grown to the 12.5 px floor at the
# scale the deck shows them, while their places stayed fixed - 11 and 33 text-zone findings on 2.62.1
FLOOR_PARTS = {
    "flammability": {"size": [640, 390], "label": "flammability", "parts": [
        {"id": "F", "type": "flammability", "x": 70, "y": 40, "w": 540, "h": 260, "xmax": 100, "ymax": 25, "air": 21,
         "xlabel": "% fuel gas in the mixture", "ylabel": "% oxygen", "zone": [[5, 19.95], [15, 17.85], [6, 12]], "value": 0}]},
    "step_track": {"size": [640, 390], "label": "step track", "parts": [
        {"id": "ST", "type": "step_track", "x": 24, "y": 30, "vertical": True, "gap": 62,
         "steps": ["Authorise", "Isolate", "Ventilate", "Test the air", "Attendant, rescue", "Enter, keep testing"]}]}}


def probe_cache_part(tmp):
    """2.63.3 (the 2.63.2 full-course run: figures half of every build, 2,900 studio probes / 17,496 s) - a probe whose page
    and every file it loads are unchanged is answered from the cache, with the very report a fresh probe gives; a changed
    spec, or a changed file the page loads, is measured again"""
    print("\n-- 2.63.3: the probe cache")
    cache = os.path.join(tmp, "probe_cache")
    parts_js = os.path.join(tmp, "parts_cache.js")
    io.open(parts_js, "w", encoding="utf-8").write("/* no extra parts */\n")
    sp = os.path.join(tmp, "cached.kit.json")
    io.open(sp, "w", encoding="utf-8").write(json.dumps(BAD))
    runs = [0]
    real = studio._Run.__init__

    def counting(self, *a, **k):
        runs[0] += 1
        return real(self, *a, **k)
    studio._Run.__init__ = counting
    old = os.environ.get("CF_PROBE_CACHE")
    try:
        def probe():
            runs[0] = 0
            r, why = studio.run(sp, parts=parts_js, panel="two-col", out=os.path.join(tmp, "pc"), shots=False)
            return r, runs[0]
        os.environ["CF_PROBE_CACHE"] = "off"
        fresh, n0 = probe()
        os.environ["CF_PROBE_CACHE"] = cache
        first, n1 = probe()
        again, n2 = probe()
        strip = lambda r: {k: {kk: vv for kk, vv in v.items() if kk != "virt"} for k, v in r["sizes"].items()}
        check("a probe the cache has answered is not run again (fresh %d browsers, first %d, again %d)" % (n0, n1, n2),
              n0 == 2 and n1 == 2 and n2 == 0, (n0, n1, n2))
        check("... and its findings are identical to a fresh probe's (every step, every check, both sizes)",
              studio.problems(fresh) == studio.problems(first) == studio.problems(again) and studio.problems(fresh)
              and strip(fresh) == strip(again), (studio.problems(fresh), studio.problems(again)))
        spec = json.loads(json.dumps(BAD))
        spec["parts"][1]["label"] = "fuel tank 2"
        io.open(sp, "w", encoding="utf-8").write(json.dumps(spec))
        _, n3 = probe()
        check("a changed spec is measured again (%d browsers)" % n3, n3 == 2, n3)
        io.open(parts_js, "w", encoding="utf-8").write("/* a changed file the page loads */\n")
        _, n4 = probe()
        check("a changed file the page loads is measured again (%d browsers)" % n4, n4 == 2, n4)
    finally:
        studio._Run.__init__ = real
        if old is None:
            os.environ.pop("CF_PROBE_CACHE", None)
        else:
            os.environ["CF_PROBE_CACHE"] = old


def floor_parts_part(tmp):
    """2.63.0 - the kit keeps a part's own words clear at the floor: the flammability chart's numbers move off its axis, the
    step track's discs grow with their digits (never into a neighbour) - judged by the drawing audit at scale ~0.6"""
    print("\n-- 2.63.0: a part's own words keep clear of its shapes at the 12.5 px floor")
    for name, spec in FLOOR_PARTS.items():
        p = os.path.join(tmp, "fp_%s.kit.json" % name)
        io.open(p, "w", encoding="utf-8").write(json.dumps(spec))
        r, why = studio.run(p, panel="420x300", sizes=((1280, 800),), out=os.path.join(tmp, "fp_" + name), shots=False)
        v = ((r or {}).get("sizes") or {}).get("1280x800") or {}
        zone = [f for st in v.get("states") or [] for f in st.get("findings") or []
                if f.get("check") in ("text zone", "inside") and re.search(r"kit-tick|kit-badge-t", f.get("part", ""))]
        rep = v.get("report") or {}
        check("%s: drawn below 1:1 (scale %s, words grown %s x) - no number on its axis or its ring" % (name, rep.get("scale"), rep.get("up")),
              r and (rep.get("up") or 0) > 1.3 and not zone, zone[:4] or why)


# 2.63.2 (item 8): IGF M06 s03 and M07 s02 as the 2.63.0 full-course build wrote them - the old form (fuel across 0-100,
# oxygen up), which the instructors called wrong ("Flamability diagram is wrong", review 2026-10-21, M06 3/21, M07 2/18)
FL_M06 = {"size": [640, 390], "label": "flammability M06", "idle": "Press Next step", "parts": [
    {"id": "FD", "type": "flammability", "x": 70, "y": 30, "w": 520, "h": 310,
     "zone": [[5, 19.95], [15, 17.85], [6, 12]], "zoneLabel": "flammable zone", "airLabel": "air line",
     "lines": [{"label": "below 12 % oxygen nothing burns", "pts": [[0, 12], [100, 12]]}],
     "path": [[0, 21], [10, 18.9], [0, 21], [0, 5], [90, 0]], "value": 0}],
    "steps": [{"title": "1", "play": [["FD", 0.07, 1500, 0, "linear"]]}, {"title": "2", "play": [["FD", 0.14, 1000, 0, "linear"]]},
              {"title": "3", "play": [["FD", 0.41, 1800, 0, "linear"]]}, {"title": "4", "play": [["FD", 1, 2200, 0, "linear"]]}]}
FL_M07 = {"size": [640, 390], "label": "flammability M07", "idle": "Press Next step", "parts": [
    {"id": "FD", "type": "flammability", "x": 70, "y": 30, "w": 520, "h": 310,
     "zone": [[5, 19.95], [15, 17.85], [6, 12]], "zoneLabel": "flammable zone", "airLabel": "air line",
     "lines": [{"label": "5 % oxygen - the inert limit", "pts": [[0, 5], [100, 5]]}],
     "path": [[0, 21], [10, 18.9], [0, 21], [0, 5], [90, 0], [2, 0], [2, 21]], "value": 0}],
    "steps": [{"title": "1", "play": [["FD", 0.0, 400, 0, "linear"]]}, {"title": "2", "play": [["FD", 0.043, 1500, 0, "linear"]]},
              {"title": "3", "play": [["FD", 0.087, 1000, 0, "linear"]]}, {"title": "4", "play": [["FD", 0.537, 3000, 0, "linear"]]},
              {"title": "5", "play": [["FD", 1, 3000, 0, "linear"]]}]}
# the standard form: methane by the part's defaults, a path in legs
FL_NEW = {"size": [640, 390], "label": "flammability", "parts": [
    {"id": "FD", "type": "flammability", "x": 70, "y": 40, "w": 520, "h": 290, "by": "legs", "zoneLabel": "flammable zone",
     "path": [[20.9, 0], [18.81, 10], [20.9, 0], [5, 0], [4, 20], [0.4, 2], [20.9, 0]], "segClass": {"0": "bad", "5": "air"}}],
    "steps": [{"title": str(n), "play": [["FD", n, 600, 0, "linear"]]} for n in (1, 3, 4, 6)]}
FL_JS = """var P=f.parts.FD, F=P.__fl, ux=F.sx(1), y0=F.sy(0), uy=F.sy(0)-F.sy(1);
function d(q){return q&&[+(q[0]).toFixed(2), +(q[1]).toFixed(2)];}
var o={old:F.old, zone:F.zone.map(d), air:F.air.map(d), crit:d(F.crit), st:[], dot:[]};
for(var k=0;k<=f.steps();k++){f.go(k,true); if(f.flush)f.flush();
  var c=svg.querySelector('.kit-flammability-dot');
  o.st.push(svg.querySelector('.kit-flammability-st').textContent);
  o.dot.push([+(+c.getAttribute('cx')/ux).toFixed(2), +((y0-c.getAttribute('cy'))/uy).toFixed(2)]);
  if(!k) o.shown0=[].filter.call(svg.querySelectorAll('.kit-flammability-trail'),function(t){return t.style.visibility!=='hidden';}).length;}
o.bad=svg.querySelectorAll('.kit-flammability-trail-bad').length; o.green=svg.querySelectorAll('.kit-flammability-trail-air').length;
return o;"""


def flammability_part(tmp):
    """2.63.2 - the kit's flammability part is the standard (ISGOTT / SIGTTO) flammability composition diagram: oxygen
    across, fuel up, the air line from air, the zone between the LFL and UFL with its nose, the line of critical dilution;
    the old specs are read into it and their steps stop where they did; both IGF specs and the new form draw clean"""
    print("\n-- 2.63.2: the flammability diagram is the standard one (oxygen across, fuel up)")
    near = lambda a, b, t=0.06: a is not None and b is not None and all(abs(x - y) <= t for x, y in zip(a, b))
    v = kit_eval(FL_NEW, FL_JS, 700)
    check("the zone: LFL 5 % and UFL 15 % on the air line (19.86 / 17.77 % oxygen), the nose at 12 % oxygen, 6 % fuel",
          v and not v["old"] and len(v["zone"]) == 3 and near(v["zone"][0], (19.86, 5)) and near(v["zone"][1], (17.77, 15))
          and near(v["zone"][2], (12, 6)), v)
    check("the air line runs from air (20.9 % oxygen, no fuel) up to the left (16.72 % at 20 % fuel)",
          v and near(v["air"][0], (20.9, 0)) and near(v["air"][1], (16.72, 20)), v)
    check("the line of critical dilution with air: from air past the nose to the fuel axis (20.9 x 6 / 8.9 = 14.09 %)",
          v and near(v["crit"], (0, 14.09)), v)
    check("legs: step 1 in the zone (FLAMMABLE), the others - back to air, inerted, gassed up, gas-freed - outside it",
          v and v["st"] == ["NOT FLAMMABLE", "FLAMMABLE", "NOT FLAMMABLE", "NOT FLAMMABLE", "NOT FLAMMABLE"]
          and near(v["dot"][1], (18.81, 10)) and near(v["dot"][2], (5, 0)) and near(v["dot"][3], (4, 20))
          and near(v["dot"][4], (20.9, 0)), v)
    check("segClass: the forbidden leg amber, the way back to air green", v and v["bad"] == 1 and v["green"] == 1, v)
    check("at rest no leg is drawn - not even its round cap as a dot (the visual check saw dots at the path's corners)",
          v and v.get("shown0") == 0, v)
    for name, spec, st in (("M06 s03", FL_M06, ["NOT FLAMMABLE", "FLAMMABLE"] + ["NOT FLAMMABLE"] * 3),
                           ("M07 s02", FL_M07, ["NOT FLAMMABLE"] * 2 + ["FLAMMABLE"] + ["NOT FLAMMABLE"] * 3)):
        v = kit_eval(spec, FL_JS, 700)
        check("IGF %s in the old form is read as it: oxygen across, its zone and lines turned, its steps stop as before (%s)"
              % (name, "/".join(x[:3] for x in st)),
              v and v["old"] and near(v["zone"][0], (19.95, 5)) and near(v["zone"][2], (12, 6)) and v["st"] == st
              and near(v["air"][0], (21, 0)), v)
        if v and name == "M06 s03":
            check("... M06's step 3 is inerted (under 5 % oxygen, little fuel), step 4 gassed up at the top of the scale",
                  v["dot"][3][0] < 5.5 and v["dot"][3][1] < 3 and near(v["dot"][4], (0, 20)), v["dot"])
        p = os.path.join(tmp, "fl_%s.kit.json" % name[:3])
        io.open(p, "w", encoding="utf-8").write(json.dumps(spec))
        r, why = studio.run(p, panel="two-col", sizes=((1280, 800), (1024, 768)), step="all", out=os.path.join(tmp, "fl_" + name[:3]), shots=False)
        check("IGF %s draws clean at 1280 x 800 and 1024 x 768, every step" % name, r and not findings(r), (findings(r) if r else why))


# 2.63.2 (item 15) - the kit's own flaws found when the realistic kit replaced the old one in the IGF original course
# (review_fixes CHANGES.md "Kit replaced"): IGF M06 s11 and M03 s06 as they stood before the hand fixes
WORDS_M06S11 = {"size": [640, 390], "parts": [
    {"id": "ACC", "type": "space", "x": 442, "y": 40, "w": 190, "h": 210, "style": "enclosure", "label": "accommodation"},
    {"id": "SP", "type": "spill", "x": 6, "y": 100, "w": 628, "surface": "deck", "surfaceY": 150, "from": 170, "reach": 150, "label": "deck", "value": 0},
    {"id": "C1", "type": "gas_cloud", "x": 30, "y": 160, "w": 300, "h": 90, "from": [146, 76], "value": 0},
    {"id": "C2", "type": "gas_cloud", "x": 300, "y": 160, "w": 190, "h": 90, "from": [10, 76], "value": 0},
    {"id": "AIR", "type": "fan", "x": 442, "y": 214, "dir": "right", "r": 18, "len": 64, "label": "air intake", "state": False, "value": 0},
    {"id": "W", "type": "wind", "x": 30, "y": 30, "w": 330, "rows": 3, "gap": 26, "dir": 0, "label": "light wind", "words": ["CALM", "LIGHT", "LIGHT", "STRONG"], "value": 0},
    {"type": "text", "x": 120, "y": 140, "to": [176, 230], "style": "cap", "text": "rich - too rich to burn"},
    {"type": "text", "x": 300, "y": 140, "to": [330, 232], "style": "cap", "text": "flammable"},
    {"type": "text", "x": 400, "y": 300, "to": [470, 238], "style": "cap", "text": "lean"}],
    "steps": [{"play": [["SP", 1, 2600, 0, "linear"]]}, {"play": [["C1", 1, 2600, 0, "linear"]]}, {"play": [["C1", 1, 300]]},
              {"play": [["W", 0.3, 800], ["C2", 1, 2800, 0, "linear"], ["AIR", 1, 600, 1800]]}]}
WORDS_M03S06 = {"size": [625, 373], "parts": [
    {"type": "text", "x": 290, "y": 30, "text": "boil-off gas"}, {"id": "BO", "type": "boil_off", "x": 30, "y": 90, "w": 225, "h": 125},
    {"type": "text", "x": 142, "y": 292, "style": "h", "text": "LNG fuel tank"},
    {"id": "G", "type": "pipe", "fluid": "gas", "d": "M142 90 V46 H566 V110", "value": 0},
    {"id": "GB", "type": "pipe", "fluid": "gas", "d": "M380 46 V185", "value": 0},
    {"id": "VG", "type": "valve", "x": 380, "y": 118, "rotate": 90, "labelAt": "right", "trip": False, "value": 0},
    {"id": "GCU", "type": "space", "x": 312, "y": 185, "w": 136, "h": 78, "style": "enclosure", "label": "GAS\nCOMBUSTION\nUNIT"},
    {"id": "E", "type": "engine", "x": 518, "y": 120, "w": 96, "h": 62, "label": "engine", "value": 0}],
    "steps": [{"play": [["BO", 1, 1200]]}, {"play": [["G", 1, 500], ["E", 1, 400]]}, {"play": [["VG", 1, 600], ["GB", 1, 400, 300], ["GCU", 1, 500, 300]]}]}
# a cloud listed after a part whose words it covers (IGF M06 s04: "hot exhaust 540 °C", "lamp not certified safe")
WORDS_VEIL = {"size": [640, 360], "parts": [
    {"id": "R", "type": "space", "x": 40, "y": 40, "w": 560, "h": 280, "label": "FUEL PREPARATION ROOM", "style": "room"},
    {"id": "V", "type": "valve", "x": 300, "y": 180, "label": "fuel valve"},
    {"id": "C", "type": "gas_cloud", "x": 40, "y": 40, "w": 560, "h": 280, "from": [260, 200], "value": 1}]}
WORDS_JS = r"""
var st = document.createElement('style'); st.textContent = '*{transition:none!important;animation:none!important}'; document.head.appendChild(st);
function rgba(s){var m=/rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)(?:[ ,/]+([\d.]+%?))?\s*\)/.exec(s||'');if(!m)return null;var a=m[4]===undefined?1:(/%$/.test(m[4])?parseFloat(m[4])/100:parseFloat(m[4]));return [+m[1],+m[2],+m[3],a];}
function lum(c){function l(v){v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);}return 0.2126*l(c[0])+0.7152*l(c[1])+0.0722*l(c[2]);}
function ratio(a,b){var x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
function op(n){var o=1;for(var e=n;e&&e!==svg.parentNode;e=e.parentNode){var cs=getComputedStyle(e);if(cs.display==='none'||cs.visibility==='hidden')return 0;var v=parseFloat(cs.opacity);if(!isNaN(v))o*=v;}return o;}
function hit(a,b){return a.left<b.right-1&&a.right>b.left+1&&a.top<b.bottom-1&&a.bottom>b.top+1;}
var panel=rgba(getComputedStyle(svg.parentNode).backgroundColor)||[12,30,58,1], low=[], veiled=[], n=f.steps();
for(var k=0;k<=n;k++){ f.go(k,true);
  var puffs=[].filter.call(svg.querySelectorAll('[data-veil]'),function(p){return op(p)>0.05;});
  [].forEach.call(svg.querySelectorAll('text.kit-sl,text.kit-cap,text.kit-h,text.kit-state'),function(t){
    if(op(t)<0.5||!t.textContent.trim())return; var r=t.getBoundingClientRect(); if(!r.width)return;
    puffs.forEach(function(p){ if((t.compareDocumentPosition(p)&4)&&hit(r,p.getBoundingClientRect())) veiled.push(k+':'+t.textContent.trim()); });
    var under=document.elementsFromPoint(r.left+r.width/2,r.top+r.height/2), g=panel;
    for(var i=0;i<under.length;i++){var u=under[i]; if(u===svg||!svg.contains(u))break; if(/^(text|tspan|g|line|polyline)$/i.test(u.tagName))continue;
      var cs=getComputedStyle(u),c=rgba(cs.fill),fo=parseFloat(cs.fillOpacity); if(!c||c[3]<0.5||(!isNaN(fo)&&fo<0.5)||op(u)<0.5)continue; g=c; break;}
    var ts=getComputedStyle(t), fc=rgba(ts.fill), sc=rgba(ts.stroke), sw=parseFloat(ts.strokeWidth)||0;
    if(!fc)return; var halo=sc&&sw>=2.5&&ts.paintOrder.indexOf('stroke')===0?ratio(fc,sc):0;
    if(ratio(fc,g)<3&&halo<4.5) low.push(k+':'+t.textContent.trim()+' '+ratio(fc,g).toFixed(2));
  });}
return {low: low, veiled: veiled};"""


def kit_words_part():
    """2.63.2 - the kit's words read on whatever they stand on, at every step: a ground that is not shown yet is no ground
    (dark ink was printed on the navy panel over a cloud still to come - IGF M06 s11 "air intake" 1.4:1), a part's own word
    on its light contents gets the dark ink (M03 s06 "LNG" on the liquid, 2:1), a room's name not lit is the readable grey,
    and a vapour cloud is never drawn over a word"""
    print("\n-- 2.63.2: the kit's words read on their ground at every step; a cloud never covers a word")
    for name, spec in (("IGF M06 s11", WORDS_M06S11), ("IGF M03 s06", WORDS_M03S06), ("a cloud after a labelled valve", WORDS_VEIL)):
        for wd in (680, 443):
            v = kit_eval(spec, WORDS_JS, wd)
            check("%s at %d px: no word under 3:1 on its ground (none with a halo under 4.5:1), none under a cloud drawn after it"
                  % (name, wd), v and not v["low"] and not v["veiled"], v)
    css = io.open(os.path.join(studio.KIT, "kit.css"), encoding="utf-8").read()
    rule = re.search(r"\.kit-sl\{[^}]*\}", css)
    check("a room's name not lit is --dim-d (was --faint-d, 2.6:1 on the hull: IGF M01 s03 / s04, M02 s12)",
          rule and "fill:var(--dim-d" in rule.group(0), rule and rule.group(0)[:160])


if __name__ == "__main__":
    sys.exit(main())
