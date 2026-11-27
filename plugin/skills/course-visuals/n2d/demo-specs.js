/* The demo figures: every form and scene on real content (example words; a course's sources decide the real ones). */
window.N2D_DEMOS = [
 {
  "topic": "Marine engineering",
  "title": "Starting a centrifugal pump",
  "lines": [
   "Suction open, discharge valve shut, pump stopped.",
   "Start the pump against the shut valve: pressure builds, nothing flows.",
   "Open the discharge valve slowly: oil flows and the pressure settles."
  ],
  "spec": {
   "form": "scene",
   "scene": "pump_line",
   "say": "A centrifugal pump is started against a shut discharge valve, then the valve is opened slowly.",
   "from": {
    "name": "Settling tank",
    "level": 0.78
   },
   "to": {
    "name": "Service tank",
    "level": 0.22
   },
   "parts": [
    "filter",
    "pump",
    "gauge",
    "valve"
   ],
   "names": {
    "valve": "Discharge valve"
   },
   "steps": [
    {
     "line": 1
    },
    {
     "line": 2,
     "pump": "on",
     "tag": {
      "gauge": "Pressure up, no flow"
     }
    },
    {
     "line": 3,
     "valve": "open",
     "tag": {
      "valve": "Open slowly"
     }
    }
   ]
  }
 },
 {
  "topic": "Navigation",
  "title": "Crossing: who gives way?",
  "lines": [
   "The bearing of the other ship does not change: risk of collision.",
   "She is on your starboard side: you see her red light, you give way.",
   "Alter to starboard early and pass astern of her."
  ],
  "spec": {
   "form": "scene",
   "scene": "crossing",
   "say": "A steady bearing means risk of collision; the ship that has the other on her starboard side gives way and passes astern.",
   "own": {
    "name": "Own ship"
   },
   "other": {
    "name": "Other ship"
   },
   "steps": [
    {
     "line": 1,
     "show": "start"
    },
    {
     "line": 1,
     "show": "bearing"
    },
    {
     "line": 2,
     "show": "lights"
    },
    {
     "line": 3,
     "show": "alter"
    }
   ]
  }
 },
 {
  "topic": "Safety procedure",
  "title": "Entering an enclosed space",
  "lines": [
   "A permit is signed before anyone goes in.",
   "The space is isolated and ventilated.",
   "The air is tested before entry and while inside.",
   "An attendant stays at the entrance throughout."
  ],
  "spec": {
   "form": "steps",
   "tone": "teal",
   "say": "Nobody enters before the permit, isolation, ventilation, an air test and an attendant are in place.",
   "steps": [
    {
     "line": 1,
     "is": "permit",
     "do": "Permit signed"
    },
    {
     "line": 2,
     "is": "padlock",
     "do": "Isolate the space"
    },
    {
     "line": 2,
     "is": "fan",
     "do": "Ventilate"
    },
    {
     "line": 3,
     "is": "detector",
     "do": "Test the air",
     "read": "O₂ 21 %"
    },
    {
     "line": 4,
     "is": "attendant",
     "do": "Attendant at the entrance"
    },
    {
     "line": 3,
     "is": "manhole",
     "do": "Enter, keep testing"
    }
   ]
  }
 },
 {
  "topic": "IT security",
  "title": "Keep the networks apart",
  "lines": [
   "Segregation is one of the most effective ways to stop a cyber incident.",
   "OT should be physically separate from IT and public networks.",
   "Firewalls and switches between segments; separate VLANs.",
   "A wireless network is treated as uncontrolled."
  ],
  "spec": {
   "form": "zones",
   "hull": true,
   "wall": "Firewall",
   "say": "Walls between the networks keep malware from a crew laptop out of the engine control.",
   "zones": [
    {
     "id": "ot",
     "name": "OT",
     "tone": "orange",
     "things": [
      {
       "is": "engine",
       "name": "Main engine"
      },
      {
       "is": "screen",
       "name": "Alarm system"
      }
     ]
    },
    {
     "id": "it",
     "name": "Office IT",
     "tone": "blue",
     "things": [
      {
       "is": "pc",
       "name": "Office PC"
      },
      {
       "is": "server",
       "name": "File server"
      }
     ]
    },
    {
     "id": "crew",
     "name": "Crew Wi-Fi",
     "tone": "violet",
     "things": [
      {
       "is": "laptop",
       "name": "Crew laptop"
      },
      {
       "is": "wifi",
       "name": "Access point"
      }
     ]
    }
   ],
   "steps": [
    {
     "line": 1
    },
    {
     "line": 1,
     "bug": "crew",
     "tag": {
      "ot": "Engine hit too"
     }
    },
    {
     "line": 2,
     "walls": true
    },
    {
     "line": 3,
     "bug": "crew"
    },
    {
     "line": 4,
     "mark": "crew",
     "tag": {
      "crew": "Treat as untrusted"
     }
    }
   ]
  }
 },
 {
  "topic": "Engine-room systems",
  "title": "Engine data: from sensor to shore",
  "lines": [
   "Sensors send readings to local controllers.",
   "The alarm and monitoring system gathers them and raises alarms.",
   "Control systems act; maintenance data is synchronised with the office.",
   "Remote monitoring sends chosen readings ashore."
  ],
  "spec": {
   "form": "path",
   "say": "An engine reading travels from the sensor to the alarm system and out to the office ashore.",
   "steps": [
    {
     "line": 1,
     "go": "s>c"
    },
    {
     "line": 2,
     "go": "c>a",
     "tag": {
      "a": "Screens and alarms"
     }
    },
    {
     "line": 4,
     "go": "a>f>v>o",
     "tag": {
      "o": "Maker or company"
     }
    },
    {
     "line": 4,
     "mark": "f",
     "tag": {
      "f": "Also a way in"
     }
    }
   ],
   "things": [
    {
     "id": "s",
     "is": "sensor",
     "name": "Oil temp sensor",
     "tone": "orange"
    },
    {
     "id": "c",
     "is": "controller",
     "name": "Local controller",
     "tone": "orange"
    },
    {
     "id": "a",
     "is": "screen",
     "name": "Alarm system",
     "tone": "orange"
    },
    {
     "id": "f",
     "is": "firewall",
     "name": "Firewall"
    },
    {
     "id": "v",
     "is": "vsat",
     "name": "Satellite link"
    },
    {
     "id": "o",
     "is": "office",
     "name": "Office ashore",
     "tone": "slate"
    }
   ],
   "links": [
    "s>c>a>f>v>o"
   ]
  }
 },
 {
  "topic": "Project management",
  "title": "From a change request to a decision",
  "lines": [
   "Every change request is assessed for cost, time and risk.",
   "Within budget: the project manager approves it.",
   "Over budget: the sponsor decides.",
   "Either way, the plan is updated."
  ],
  "spec": {
   "form": "path",
   "tone": "violet",
   "say": "A small change is approved by the project manager; a big one goes to the sponsor first.",
   "things": [
    {
     "id": "r",
     "is": "change",
     "name": "Change request",
     "tone": "violet"
    },
    {
     "id": "m",
     "is": "manager",
     "name": "Project manager",
     "tone": "blue"
    },
    {
     "id": "d",
     "is": "decision",
     "name": "Within budget?",
     "tone": "orange"
    },
    {
     "id": "s",
     "is": "sponsor",
     "name": "Sponsor",
     "tone": "rose"
    },
    {
     "id": "p",
     "is": "plan",
     "name": "Updated plan",
     "tone": "teal"
    }
   ],
   "links": [
    "r>m>d",
    "d>p:Yes",
    "d>s:No",
    "s>p"
   ],
   "steps": [
    {
     "line": 1,
     "go": "r>m",
     "tag": {
      "m": "Cost, time, risk"
     }
    },
    {
     "line": 2,
     "go": "m>d>p",
     "tag": {
      "p": "Small change"
     }
    },
    {
     "line": 3,
     "clear": true,
     "go": "r>m>d>s",
     "tag": {
      "s": "Big change"
     }
    },
    {
     "line": 4,
     "go": "s>p"
    }
   ]
  }
 },
 {
  "topic": "Communications",
  "title": "Ship-to-shore connections",
  "lines": [
   "GEO satellite: wide cover, each answer takes longer.",
   "LEO satellites: nearer and moving, a shorter delay.",
   "Mobile network: quick and cheap near the coast, out of reach far from land."
  ],
  "spec": {
   "form": "options",
   "say": "Far from land only satellites reach; a low orbit answers faster.",
   "options": [
    {
     "is": "satellite",
     "name": "GEO satellite",
     "tone": "blue"
    },
    {
     "is": "constellation",
     "name": "LEO satellites",
     "tone": "teal"
    },
    {
     "is": "mast",
     "name": "Mobile mast",
     "tone": "violet"
    }
   ],
   "qualities": [
    {
     "name": "Reach",
     "values": [
      3,
      3,
      1
     ],
     "words": [
      "Wide",
      "Wide",
      "Near coast"
     ]
    },
    {
     "name": "Delay",
     "values": [
      3,
      1,
      1
     ],
     "low": true,
     "words": [
      "Longer",
      "Shorter",
      "Short"
     ]
    }
   ],
   "steps": [
    {
     "line": 1,
     "show": 1,
     "race": 1
    },
    {
     "line": 2,
     "show": 2,
     "race": 1,
     "tag": {
      "1": "Answers sooner"
     }
    },
    {
     "line": 3,
     "show": 2,
     "pick": 2,
     "tag": {
      "2": "Only near land"
     }
    },
    {
     "line": 4,
     "show": 2
    }
   ]
  }
 },
 {
  "topic": "Meteorology (a new subject)",
  "title": "A falling barometer",
  "lines": [
   "Read the barometer every three hours.",
   "A fall of 3.6 to 6 hPa in three hours is \"falling quickly\".",
   "A fast fall warns of strong wind coming."
  ],
  "spec": {
   "form": "amounts",
   "say": "The faster the pressure falls in three hours, the stronger the wind to expect.",
   "x": {
    "name": "Time",
    "unit": "h"
   },
   "y": {
    "name": "Pressure",
    "unit": "hPa"
   },
   "series": [
    {
     "name": "Pressure",
     "tone": "blue",
     "pts": [
      [
       0,
       1013
      ],
      [
       3,
       1012
      ],
      [
       6,
       1009
      ],
      [
       9,
       1003
      ],
      [
       12,
       997
      ]
     ]
    }
   ],
   "scale": {
    "name": "Fall in 3 hours",
    "bands": [
     {
      "to": 1.5,
      "name": "Slowly"
     },
     {
      "to": 3.5,
      "name": "Falling"
     },
     {
      "to": 6,
      "name": "Quickly"
     },
     {
      "to": 99,
      "name": "Very rapidly"
     }
    ]
   },
   "steps": [
    {
     "line": 1,
     "upto": 3,
     "span": [
      0,
      3
     ]
    },
    {
     "line": 2,
     "upto": 9,
     "span": [
      6,
      9
     ]
    },
    {
     "line": 3,
     "upto": 12,
     "span": [
      9,
      12
     ],
     "tag": "Expect strong wind"
    }
   ]
  }
 },
 {
  "topic": "IT course M03 s03",
  "title": "Explore: open each device",
  "lines": [
   "A small ship's network is drawn on the screen: router, firewall, two switches, an access point, a server, three PCs.",
   "Tap a device and say aloud what it does before the label shows.",
   "Then follow one cable from a crew PC to the link to shore: which devices does the data pass, in which order?"
  ],
  "spec": {
   "form": "path",
   "say": "A crew PC reaches shore through the switch, the firewall, the router and the satellite link.",
   "steps": [
    {
     "line": 1
    },
    {
     "line": 2,
     "mark": [
      "sw",
      "fw"
     ],
     "tag": {
      "fw": "What does it do?"
     }
    },
    {
     "line": 3,
     "go": "pc>sw>fw>rt>v",
     "tag": {
      "v": "Out to shore"
     }
    }
   ],
   "things": [
    {
     "id": "pc",
     "is": "pc",
     "name": "Crew PC"
    },
    {
     "id": "ap",
     "is": "wifi",
     "name": "Access point"
    },
    {
     "id": "srv",
     "is": "server",
     "name": "File server"
    },
    {
     "id": "sw",
     "is": "switch",
     "name": "Switch"
    },
    {
     "id": "fw",
     "is": "firewall",
     "name": "Firewall"
    },
    {
     "id": "rt",
     "is": "router",
     "name": "Router"
    },
    {
     "id": "v",
     "is": "vsat",
     "name": "Link to shore"
    }
   ],
   "links": [
    "pc>sw",
    "ap>sw",
    "srv>sw",
    "sw>fw>rt>v"
   ]
  }
 },
 {
  "topic": "IT course M03 s09",
  "title": "IT, OT and IoT",
  "lines": [
   "IT refers to computer-based systems focused on the use of data as information (IMO).",
   "OT uses data to control or watch a physical process: IMO's example is the main engine's oil temperature sent to the control room.",
   "BIMCO: Industrial IoT is the application of instrumentation and connected sensors and other devices to machinery and vehicles.",
   "Vulnerabilities in OT systems may increase the operational safety risks of ships that may jeopardize the safety of both crew and passengers."
  ],
  "spec": {
   "form": "zones",
   "say": "IT handles information, OT runs a physical process, IoT connects sensors on machinery.",
   "zones": [
    {
     "id": "it",
     "name": "IT",
     "tone": "blue",
     "things": [
      {
       "is": "pc",
       "name": "Office PC"
      },
      {
       "is": "server",
       "name": "Mail server"
      }
     ]
    },
    {
     "id": "ot",
     "name": "OT",
     "tone": "orange",
     "things": [
      {
       "is": "engine",
       "name": "Main engine"
      },
      {
       "is": "screen",
       "name": "Control-room screen"
      }
     ]
    },
    {
     "id": "iot",
     "name": "IoT",
     "tone": "violet",
     "things": [
      {
       "is": "sensor",
       "name": "Connected sensor"
      },
      {
       "is": "globe",
       "name": "Maker online"
      }
     ]
    }
   ],
   "steps": [
    {
     "line": 1,
     "mark": "it",
     "tag": {
      "it": "Information"
     }
    },
    {
     "line": 2,
     "mark": "ot",
     "tag": {
      "ot": "A physical process"
     }
    },
    {
     "line": 3,
     "mark": "iot",
     "tag": {
      "iot": "Sensors on machinery"
     }
    },
    {
     "line": 4,
     "mark": "ot",
     "tag": {
      "ot": "Safety at risk"
     }
    }
   ]
  }
 },
 {
  "topic": "IT course M03 s11",
  "title": "Scenario: what is wrong with this drawing?",
  "lines": [
   "A previous officer's sketch shows the control-room workstation on a switch that also serves a mess-room wall socket. A visitor plugs in a laptop that carries malware.",
   "One cable joins two zones that should be apart."
  ],
  "spec": {
   "form": "path",
   "say": "One cable joins the mess-room socket to the control-room switch, so a visitor's laptop reaches OT.",
   "things": [
    {
     "id": "lp",
     "is": "laptop",
     "name": "Visitor laptop",
     "tone": "violet"
    },
    {
     "id": "so",
     "is": "socket",
     "name": "Mess-room socket",
     "tone": "violet"
    },
    {
     "id": "sw",
     "is": "switch",
     "name": "Shared switch"
    },
    {
     "id": "ws",
     "is": "pc",
     "name": "Control-room PC",
     "tone": "orange"
    }
   ],
   "links": [
    "lp>so>sw>ws"
   ],
   "steps": [
    {
     "line": 1
    },
    {
     "line": 1,
     "bug": "lp>so>sw>ws",
     "tag": {
      "ws": "Malware reaches OT"
     }
    },
    {
     "line": 2,
     "wrong": "so>sw",
     "mark": "sw",
     "tag": {
      "sw": "Two zones, one switch"
     }
    }
   ]
  }
 },
 {
  "topic": "IT course M03 s12",
  "title": "Bridge systems share data",
  "lines": [
   "In this example arrangement, sensors send data to the systems that use it: GNSS gives position and time; the gyro compass gives heading.",
   "In this example arrangement, radar and ARPA, AIS and ECDIS take data from them and add their own.",
   "IEC 61162 is the series of standards for digital interfaces of maritime navigation and radiocommunication equipment.",
   "In this example arrangement, one sensor feeds many systems, so one failure shows up in several places at once."
  ],
  "spec": {
   "form": "path",
   "say": "Two sensors feed many bridge systems.",
   "steps": [
    {
     "line": 1
    },
    {
     "line": 2,
     "go": [
      "gnss>rd",
      "gnss>ais",
      "gnss>ec"
     ],
     "tag": {
      "gnss": "Position and time"
     }
    },
    {
     "line": 3,
     "go": [
      "gy>rd",
      "gy>ais",
      "gy>ec",
      "gy>cn"
     ],
     "tag": {
      "gy": "Heading"
     }
    },
    {
     "line": 4,
     "mark": "gy",
     "tag": {
      "gy": "One feeds four"
     }
    }
   ],
   "things": [
    {
     "id": "gnss",
     "is": "gnss",
     "name": "GNSS",
     "tone": "teal"
    },
    {
     "id": "gy",
     "is": "gyro",
     "name": "Gyro compass",
     "tone": "teal"
    },
    {
     "id": "rd",
     "is": "radar",
     "name": "Radar / ARPA"
    },
    {
     "id": "ais",
     "is": "ais",
     "name": "AIS"
    },
    {
     "id": "ec",
     "is": "ecdis",
     "name": "ECDIS"
    },
    {
     "id": "cn",
     "is": "conning",
     "name": "Conning display"
    }
   ],
   "links": [
    "gnss>rd",
    "gnss>ais",
    "gnss>ec",
    "gy>rd",
    "gy>ais",
    "gy>ec",
    "gy>cn"
   ]
  }
 },
 {
  "topic": "IT course M03 s13",
  "title": "Predict: the gyro compass stops sending",
  "lines": [
   "The ship is under way; the gyro compass stops sending heading, nothing else fails.",
   "In this example arrangement, the data lines from the gyro lead to radar and ARPA, the conning display and other systems that use heading."
  ],
  "spec": {
   "form": "path",
   "say": "When the gyro stops, every system it feeds loses heading.",
   "steps": [
    {
     "line": 1,
     "go": [
      "gnss>rd",
      "gnss>ais",
      "gnss>ec",
      "gy>rd",
      "gy>ais",
      "gy>ec",
      "gy>cn"
     ]
    },
    {
     "line": 2,
     "fail": "gy",
     "tag": {
      "gy": "Stops sending"
     }
    }
   ],
   "things": [
    {
     "id": "gnss",
     "is": "gnss",
     "name": "GNSS",
     "tone": "teal"
    },
    {
     "id": "gy",
     "is": "gyro",
     "name": "Gyro compass",
     "tone": "teal"
    },
    {
     "id": "rd",
     "is": "radar",
     "name": "Radar / ARPA"
    },
    {
     "id": "ais",
     "is": "ais",
     "name": "AIS"
    },
    {
     "id": "ec",
     "is": "ecdis",
     "name": "ECDIS"
    },
    {
     "id": "cn",
     "is": "conning",
     "name": "Conning display"
    }
   ],
   "links": [
    "gnss>rd",
    "gnss>ais",
    "gnss>ec",
    "gy>rd",
    "gy>ais",
    "gy>ec",
    "gy>cn"
   ]
  }
 },
 {
  "topic": "IT course M03 s15",
  "title": "Predict: where does a new reading go?",
  "lines": [
   "A new fuel-oil treatment unit is fitted. Its controller measures the oil temperature of the unit.",
   "The watch wants the reading on the control-room screen, and the superintendent wants it ashore."
  ],
  "spec": {
   "form": "path",
   "say": "A new unit's reading joins the same route to the control room and ashore.",
   "things": [
    {
     "id": "u",
     "is": "controller",
     "name": "New fuel unit",
     "tone": "green",
     "hidden": true
    },
    {
     "id": "a",
     "is": "screen",
     "name": "Alarm system",
     "tone": "orange"
    },
    {
     "id": "f",
     "is": "firewall",
     "name": "Firewall"
    },
    {
     "id": "v",
     "is": "vsat",
     "name": "Satellite link"
    },
    {
     "id": "o",
     "is": "office",
     "name": "Office ashore",
     "tone": "slate"
    }
   ],
   "links": [
    "u>a>f>v>o"
   ],
   "steps": [
    {
     "line": 1,
     "add": "u",
     "tag": {
      "u": "New reading"
     }
    },
    {
     "line": 2,
     "go": "u>a>f>v>o",
     "tag": {
      "o": "Superintendent"
     }
    }
   ]
  }
 },
 {
  "topic": "IT course M03 s22",
  "title": "Two faults: what do they share?",
  "lines": [
   "Fault A: one office PC has no link light. The cable tester shows a wire broken inside the plug.",
   "Fault B: every PC on one switch has lost the link to shore. Every light on the switch is on; the firewall's uplink light is dark."
  ],
  "spec": {
   "form": "path",
   "say": "Both faults are a broken link; where it breaks decides who loses shore.",
   "things": [
    {
     "id": "p1",
     "is": "pc",
     "name": "Office PC 1"
    },
    {
     "id": "p2",
     "is": "pc",
     "name": "Office PC 2"
    },
    {
     "id": "sw",
     "is": "switch",
     "name": "Switch"
    },
    {
     "id": "fw",
     "is": "firewall",
     "name": "Firewall"
    },
    {
     "id": "v",
     "is": "vsat",
     "name": "Link to shore"
    }
   ],
   "links": [
    "p1>sw",
    "p2>sw",
    "sw>fw>v"
   ],
   "steps": [
    {
     "line": 1,
     "cut": "p1>sw",
     "tag": {
      "p1": "Fault A"
     }
    },
    {
     "line": 2,
     "clear": true,
     "cut": "fw>v",
     "tag": {
      "fw": "Fault B"
     }
    },
    {
     "line": 2,
     "cut": [
      "p1>sw",
      "fw>v"
     ],
     "tag": {
      "p1": "One PC",
      "fw": "Every PC"
     }
    }
   ]
  }
 },
 {
  "topic": "IT course M03 s23",
  "title": "Worked example: a PC with no network",
  "lines": [
   "The crew-mess PC has no network → Start with the lights, not the settings",
   "Read the switch port's light → Dark: no link",
   "Test the patch cable with the tester → One wire shows broken",
   "Swap in a good cable → Link light on, PC online",
   "Write the fix down and tell shore → Device, symptom, test, fix, time"
  ],
  "spec": {
   "form": "steps",
   "tone": "blue",
   "say": "Start with the lights, test the cable, swap it, log it.",
   "steps": [
    {
     "line": 1,
     "is": "pc",
     "do": "No network",
     "read": "Crew-mess PC"
    },
    {
     "line": 2,
     "is": "switch",
     "do": "Read the port light",
     "read": "Dark: no link"
    },
    {
     "line": 3,
     "is": "tester",
     "do": "Test the cable",
     "read": "1 wire broken"
    },
    {
     "line": 4,
     "is": "cable",
     "do": "Fit a good cable",
     "read": "Link light on"
    },
    {
     "line": 5,
     "is": "document",
     "do": "Log it, tell shore"
    }
   ]
  }
 }
];
