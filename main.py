1	from ollama import chat
2	import json
3	import subprocess
4	import sys
5	import importlib
6	import types
7	import logging
8	import time
9	import traceback
10	import re
11	from collections import deque, Counter
12	from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
13	from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
14	from cryptography.hazmat.primitives import hashes, padding
15	from cryptography.hazmat.backends import default_backend
16	import os
17	import json
18	from mem0 import Memory
19	import base64
20	from test_router import get_intent_state, get_routing_decision
21	class LoopGuard:
22	    def __init__(self, max_history=20, repeat_limit=5, pattern_limit=6):
23	        self.history = deque(maxlen=max_history)
24	        self.repeat_limit = repeat_limit
25	        self.pattern_limit = pattern_limit
26	
27	    def add(self, tool_name: str):
28	        self.history.append(tool_name)
29	
30	    def too_many_repeats(self):
31	        # single tool spam check
32	        counts = Counter(self.history)
33	        return any(v >= self.repeat_limit for v in counts.values())
34	
35	    def pattern_loop(self):
36	        # detects repeating sequences like A B A B
37	        data = list(self.history)
38	
39	        for size in range(2, 5):
40	            if len(data) < size * 2:
41	                continue
42	
43	            pattern = data[-size:]
44	            repeats = 0
45	
46	            for i in range(len(data) - size, -1, -size):
47	                if data[i:i+size] == pattern:
48	                    repeats += 1
49	                else:
50	                    break
51	
52	            if repeats >= self.pattern_limit:
53	                return True
54	
55	        return False
56	
57	    def should_stop(self):
58	        return self.too_many_repeats() or self.pattern_loop()
59	logging.basicConfig(
60	    level=logging.INFO,
61	    format="%(asctime)s [%(levelname)s] %(message)s",
62	    handlers=[
63	        logging.FileHandler("server.log", encoding="utf-8"),
64	        logging.StreamHandler()
65	    ]
66	)
67	
68	logger = logging.getLogger(__name__)
69	sys.stdout.reconfigure(encoding='utf-8')
70	sys.stderr.reconfigure(encoding='utf-8')
71	import markdown
72	import requests
73	from flask import Flask,request, Response
74	app = Flask(__name__)
75	import os
76	modules = {}
77	ADDONS_DIR=os.getcwd() + "\\addons"
78	for file in os.listdir(ADDONS_DIR):
79	    if file.endswith(".py") and file != "__init__.py":
80	        module_name = file[:-3]  # strip .py
81	        full_path = f"addons.{module_name}"
82	
83	        module = importlib.import_module(full_path)
84	        modules[module_name] = module
85	model = "qwen3.5:9b"
86	OLLAMA_URL = "http://localhost:11434"
87	import getpass
88	username_computer = getpass.getuser()
89	def write_file(file_path:str,file_content:str):
90	    dir_path = os.path.dirname(file_path)
91	
92	    if dir_path and not os.path.exists(dir_path):
93	        os.makedirs(dir_path, exist_ok=True)
94	    with open(file_path,"w", encoding="utf-8") as w:
95	        w.write(file_content)
96	    return"success"
97	def read_file(file_path:str):
98	    try:
99	        with open(file_path, "r", encoding="utf-8") as r:
100	            return r.read()
101	    except FileNotFoundError:
102	        return f"[ERROR] File not found: {file_path}"
103	ps_aliases = {
104	    "rm": "remove-item",
105	    "del": "remove-item",
106	    "rd": "remove-item",
107	    "erase": "remove-item"
108	}
109	def derive_key(key: bytes | str, salt: bytes) -> bytes:
110	    """Derive a 256-bit AES key from any-length key using PBKDF2."""
111	    if isinstance(key, str):
112	        key = key.encode()
113	    kdf = PBKDF2HMAC(
114	        algorithm=hashes.SHA256(),
115	        length=32,
116	        salt=salt,
117	        iterations=600_000,
118	        backend=default_backend()
119	    )
120	    return kdf.derive(key)
121	
122	def encrypt(plaintext: str, key: bytes | str) -> str:
123	    """
124	    Encrypt a string using AES-256-CBC with any-length key.
125	    Returns a base64-encoded string: salt + IV + ciphertext.
126	    """
127	    salt = os.urandom(16)
128	    iv = os.urandom(16)
129	    derived = derive_key(key, salt)
130	
131	    padder = padding.PKCS7(128).padder()
132	    padded = padder.update(plaintext.encode()) + padder.finalize()
133	
134	    cipher = Cipher(algorithms.AES(derived), modes.CBC(iv), backend=default_backend())
135	    encryptor = cipher.encryptor()
136	    ciphertext = encryptor.update(padded) + encryptor.finalize()
137	
138	    return base64.b64encode(salt + iv + ciphertext).decode()
139	
140	def decrypt(token: str, key: bytes | str) -> str:
141	    """
142	    Decrypt a base64-encoded AES-256-CBC token with any-length key.
143	    Returns the original plaintext string.
144	    """
145	    raw = base64.b64decode(token)
146	    salt, iv, ciphertext = raw[:16], raw[16:32], raw[32:]
147	    derived = derive_key(key, salt)
148	
149	    cipher = Cipher(algorithms.AES(derived), modes.CBC(iv), backend=default_backend())
150	    decryptor = cipher.decryptor()
151	    padded = decryptor.update(ciphertext) + decryptor.finalize()
152	
153	    unpadder = padding.PKCS7(128).unpadder()
154	    return (unpadder.update(padded) + unpadder.finalize()).decode()
155	
156	def remember(memory:str):
157	    file_path = "./memory.json"
158	    content = json.loads(open(file_path,"r").read())
159	    content.append(memory)
160	    content = json.dumps(content)
161	    with open(file_path,"w") as w:
162	        w.write(content)
163	    return f"saved {memory}"
164	def normalize(cmd: str):
165	    tokens = cmd.lower().split()
166	    return [ps_aliases.get(t, t) for t in tokens]
167	badcommands = ["Remove-Item","del","rm","erase","rd","robocopy","Delete"]
168	def is_bad(cmd: str):
169	    tokens = normalize(cmd)
170	    tokens = re.split(r"[ \t;|&]+", cmd.lower())
171	    return any(bad.lower() == t for bad in badcommands for t in tokens)
172	for plugin in os.listdir("C:/Users/safra/SimpleLLM/plugins/"):
173	    if plugin.endswith(".py") and plugin != "__init__.py":
174	        subprocess.Popen([
175	            "py",
176	            f"C:/Users/safra/SimpleLLM/plugins/{plugin}"
177	        ])
178	def shell(cmd:str,cwd=None):
179	    if is_bad(cmd):
180	        return f"This command failed due to dangerous properties. Ask the user to run the command: {cmd}"
181	    try:
182	        result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True,cwd=cwd,timeout=10)
183	    except subprocess.TimeoutExpired as e:
184	        print("timed out")
185	        return e.stdout + e.stderr
186	    return result.stdout + result.stderr
187	def search(query:str):
188	    resp = requests.get(f"http://localhost:8080/?q={query}&safesearch=1&format=json")
189	    resp.encoding = "utf-8"
190	    data = resp.json()
191	    results = data.get("results", [])[:10]
192	    simplified = []
193	    for r in results:
194	        simplified.append({
195	            "title": r.get("title"),
196	            "url": r.get("url"),
197	            "snippet": r.get("content", "")[:200]
198	        })
199	
200	    return json.dumps(simplified, ensure_ascii=False)
201	def recall_memories():
202	    file_path = "./memory.json"
203	    content = json.loads(open(file_path,"r").read())
204	    formatted_memories = "\n".join(
205	        f"- {m}" for m in content
206	    )
207	    return f"MEMORIES:\n{formatted_memories}"
208	
209	tools = [{"type":"function","function":{"name":"write_file","description":"Write text to a file","parameters":{"type":"object","properties":{"file_path":{"type":"string"},"file_content":{"type":"string"}},"required":["file_path","file_content"]}}},
210	                        {"type":"function","function":{"name":"read_file","description":"Read a file from disk","parameters":{"type":"object","properties":{"file_path":{"type":"string"}},"required":["file_path"]}}},
211	                        { "type": "function", "function": { "name": "shell", "description": "Execute windows powershell command", "parameters": { "type": "object", "properties": { "cmd": {"type": "string"}, "cwd": {"type": "string"} }, "required": ["cmd"] } } },
212	                        {"type":"function","function":{"name":"search","description":"Search the web with a search engine","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
213	                        {"type":"function","function":{"name":"agent_mode","description":"Go into agent mode. Agent mode allows you to generate a goal and run it using agenti workflows. Good for large or complex projects.","parameters":{"type":"object","properties":{"goal":{"type":"string"}},"required":["goal"]}}},
214	                        {"type": "function", "function": { "name": "remember", "description": ( "Save a long-term memory entry into the assistant's persistent memory storage. " "Use this when the user shares important information, preferences, habits, " "projects, naming conventions, recurring workflows, or facts that should be " "remembered across future conversations or sessions. " "Examples include favorite coding styles, preferred file naming systems, " "project details, personal assistant behaviors, or reminders the AI should retain. " "Do NOT use for temporary context, sensitive secrets, passwords, API keys, " "or highly private information unless explicitly requested." ), "parameters": { "type": "object", "properties": { "memory": { "type": "string", "description": ( "The memory text to store permanently. " "Should be concise but descriptive enough to remain useful later. " "Example: 'User prefers snake_case filenames for Python projects.'" ) } }, "required": ["memory"] } } },{ "type": "function", "function": { "name": "recall_memories", "description": ( "Retrieve saved long-term memories about the user. " "Use when the user asks what you remember, " "what you know about them, their preferences, " "projects, habits, or previous conversations." ), "parameters": { "type": "object", "properties": {} } } }]
215	
216	def save(messages):
217	    messages = clean_messages(messages)
218	    messages = json.dumps(messages)
219	    with open("save.json","w") as w:
220	        w.write(messages)
221	def load():
222	    try:
223	        with open("save.json","r") as r:
224	            messages = r.read()
225	        return json.loads(messages)
226	    except:
227	        return {}
228	tools_agent = [{"type":"function","function":{"name":"write_file","description":"Write text to a file","parameters":{"type":"object","properties":{"file_path":{"type":"string"},"file_content":{"type":"string"}},"required":["file_path","file_content"]}}},
229	                            {"type":"function","function":{"name":"read_file","description":"Read a file from disk","parameters":{"type":"object","properties":{"file_path":{"type":"string"}},"required":["file_path"]}}},
230	                            { "type": "function", "function": { "name": "shell", "description": "Execute windows powershell command", "parameters": { "type": "object", "properties": { "cmd": {"type": "string"}, "cwd": {"type": "string"} }, "required": ["cmd"] } } },
231	                            {"type":"function","function":{"name":"search","description":"Search the web with a search engine","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
232	                            { "type": "function", "function": { "name": "remember", "description": ( "Save a long-term memory entry into the assistant's persistent memory storage. " "Use this when the user shares important information, preferences, habits, " "projects, naming conventions, recurring workflows, or facts that should be " "remembered across future conversations or sessions. " "Examples include favorite coding styles, preferred file naming systems, " "project details, personal assistant behaviors, or reminders the AI should retain. " "Do NOT use for temporary context, sensitive secrets, passwords, API keys, " "or highly private information unless explicitly requested." ), "parameters": { "type": "object", "properties": { "memory": { "type": "string", "description": ( "The memory text to store permanently. " "Should be concise but descriptive enough to remain useful later. " "Example: 'User prefers snake_case filenames for Python projects.'" ) } }, "required": ["memory"] } } },{ "type": "function", "function": { "name": "recall_memories", "description": ( "Retrieve saved long-term memories about the user. " "Use when the user asks what you remember, " "what you know about them, their preferences, " "projects, habits, or previous conversations." ), "parameters": { "type": "object", "properties": {} } } }]
233	def verifier(execution):
234	    messages = [
235	        {
236	            'role': 'system',
237	            'content': """You are a strict output validator.
238	
239	Check:
240	- completeness
241	- correctness
242	- usability
243	
244	If broken: list fixes
245	If good: output FINAL ANSWER only"""
246	        },
247	        {'role': 'user', 'content': execution}
248	    ]
249	
250	    response = chat(
251	        model='qwen2.5:7b-instruct-q4_0',
252	        messages=messages,
253	        tools=tools_agent,
254	        keep_alive="0.5m",
255	    )
256	
257	    return response.message.content
258	def executor(plan, research):
259	    messages = [
260	        {
261	            'role': 'system',
262	            'content': """You are a production-grade implementation agent.
263	
264	Build the full solution based on:
265	- plan
266	- research
267	
268	Rules:
269	- correct > clever
270	- include full code if needed
271	- structure everything clearly
272	"""
273	        },
274	        {
275	            'role': 'user',
276	            'content': f"PLAN:\n{plan}\n\nRESEARCH:\n{research}"
277	        }
278	    ]
279	
280	    response = chat(
281	        model='qwen2.5:7b-instruct-q4_0',
282	        messages=messages,
283	        tools=tools_agent,
284	        keep_alive="0.5m",
285	    )
286	
287	    return response.message.content
288	def researcher(plan):
289	    messages = [
290	        {
291	            'role': 'system',
292	            'content': """You are a focused research agent.
293	
294	Rules:
295	- no storytelling
296	- bullet facts only
297	- if unknown say UNKNOWN"""
298	        },
299	        {'role': 'user', 'content': str(plan)}
300	    ]
301	
302	    response = chat(
303	        model='qwen2.5:7b-instruct-q4_0',
304	        messages=messages,
305	        tools=tools_agent,
306	        keep_alive="0.5m",
307	    )
308	
309	    return response.message.content
310	import json
311	
312	def planner(goal):
313	    messages = [
314	        {
315	            'role': 'system',
316	            'content': """You are a system planner.
317	
318	Break the user request into:
319	- clear steps
320	- required tools (if any)
321	- risks or missing info
322	- minimal plan (do NOT over-plan)
323	
324	Output JSON only:
325	{
326	  "goal": "",
327	  "steps": [],
328	  "tools_needed": [],
329	  "risks": []
330	}"""
331	        },
332	        {'role': 'user', 'content': goal}
333	    ]
334	
335	    response = chat(
336	        model='qwen2.5:7b-instruct-q4_0',
337	        messages=messages,
338	        tools=tools_agent,
339	        keep_alive="0.5m",
340	    )
341	
342	    return json.loads(response.message.content)
343	def agent_mode(goal: str):
344	    plan_data = planner(goal)
345	    research_data = researcher(plan_data)
346	    execution = executor(plan_data, research_data)
347	    final = verifier(execution)
348	    return f"ansers: {final}, plan:{plan_data},research:{research_data},execution{execution}"
349	def clean_messages(messages):
350	    clean = {}
351	
352	    if isinstance(messages, dict):
353	        for chatid, msgs in messages.items():
354	            if not isinstance(msgs, list):
355	                continue
356	
357	            cleaned_msgs = []
358	
359	            for msg in msgs:
360	                if not isinstance(msg, dict):
361	                    continue
362	
363	                msg = msg.copy()
364	
365	                if "tool_calls" in msg and msg["tool_calls"]:
366	                    new_calls = []
367	                    for tc in msg["tool_calls"]:
368	                        try:
369	                            new_calls.append({
370	                                "function": {
371	                                    "name": tc.function.name,
372	                                    "arguments": dict(tc.function.arguments or {})
373	                                }
374	                            })
375	                        except:
376	                            pass
377	                    msg["tool_calls"] = new_calls
378	
379	                cleaned_msgs.append(msg)
380	
381	            clean[chatid] = cleaned_msgs
382	
383	    return clean
384	available_functions = {
385	    "write_file": write_file,
386	    "read_file": read_file,
387	    "shell": shell,
388	    "search":search,
389	    "agent_mode":agent_mode,
390	    "remember": remember,
391	    "recall_memories": recall_memories,
392	}
393	for name, mod in modules.items():
394	    try:
395	        available_functions[name] = mod.main
396	        tools_agent.append({"type":"function","function":{"name":name,"description":mod.description,"parameters":{"type":"object","properties":mod.args,"required":mod.required}}})
397	        tools.append({"type":"function","function":{"name":name,"description":mod.description,"parameters":{"type":"object","properties":mod.args,"required":mod.required}}})
398	    except Exception as e:
399	        print(f"INVALID FILE: {name}, Error: {e}")
400	global_messages = load()
401	def get_dominant_pattern(data, max_len=3):
402	    best_pattern = None
403	    max_count = 1
404	    
405	    # Test different pattern lengths
406	    for length in range(2, max_len + 1):
407	        patterns = find_repeating_patterns(data, length)
408	        for pattern, count in patterns.items():
409	            if count > max_count:
410	                max_count = count
411	                best_pattern = pattern
412	                
413	    return max_count
414	@app.route("/chat",methods=["GET"])
415	def api_chat():
416	    print(tools)
417	    query = request.args.get('message')
418	    query = decrypt(query,"TOP_SECRET_KEY")
419	    chatid = request.args.get('id')
420	    think = request.args.get('think')
421	    q_model = request.args.get('agent')
422	    if think == "1":
423	        think = True
424	    elif think == "0":
425	        think = False
426	    else:
427	        return "ERR: NO THINK SET"
428	    global global_messages
429	    if chatid not in global_messages:        
430	        global_messages[chatid] = [{'role': 'system', 'content': """You are SimpleLLM, a helpful and informal assistant focused on practical, correct, and runnable solutions.
431	
432	        Follow user instructions closely while thinking critically before answering. Avoid making assumptions about the user's setup, environment, or goals. When information is unclear, ask targeted questions instead of guessing.
433	
434	        Prioritize context-aware answers and adapt to the user's local environment, tools, hardware, and existing code when provided.
435	
436	        For coding tasks:
437	
438	        * Prefer generating complete files and testable code when tool support exists.
439	        * Never use port 5000.
440	        * Pass the “never use port 5000” rule to agent mode or subprocess agents.
441	        * Reason through likely bugs, edge cases, syntax issues, and runtime failures before responding.
442	        * Do not claim code was tested, compiled, or executed unless it actually was.
443	        * Focus on correct, runnable solutions over generic examples.
444	
445	        Avoid declaring tasks impossible. When limitations exist, explain them clearly and explore alternatives, workarounds, or partial solutions.
446	
447	        Use memory tools on the first message of a chat when available to recall relevant long-term user context.
448	        """}]
449	        memories = recall_memories()
450	        global_messages[chatid].append({'role':'system','content':f'Your long term memory: {memories}'})
451	    global_messages[chatid].append({'role':'user','content':query})
452	    intent_state = get_intent_state(query)
453	    think = intent_state.get("route", "fast")
454	    print(intent_state)
455	    if str(think).upper() == "THINKER":
456	        think = True
457	        print("chose think")
458	    else:
459	        think = False
460	        print("chose fast")
461	    global_messages[chatid].append({
462	        'role': 'system',
463	        'content': (
464	            "Runtime intent/state metadata for the latest user message:\n"
465	            f"{json.dumps(intent_state, ensure_ascii=False)}\n\n"
466	            "Use this to choose response style and tool posture. "
467	            "Do not mention the metadata unless it directly helps the user."
468	        )
469	    })
470	    messages = global_messages[chatid]
471	    guard = LoopGuard()
472	    def generate():
473	        try:
474	            yield "["
475	            tools_awaiting = True
476	            while True:
477	                
478	                messages = global_messages[chatid]
479	                resp = chat(
480	                    model=model if not q_model else q_model,
481	                    messages=messages,
482	                    stream=True,
483	                    tools=tools,
484	                    think=think,
485	                    keep_alive=-1,
486	                    options={
487	                        'num_thread': 8  # Limit Ollama to 4 CPU threads
488	                    }
489	                )
490	                in_thinking = False
491	                content = ''
492	                thinking = ''
493	                tool_calls = []
494	                for chunk in resp:
495	                    if chunk.message.thinking:
496	                        if not in_thinking:
497	                          in_thinking = True
498	                         
499	                        
500	                        yield json.dumps({"type": "thinking", "content": chunk.message.thinking})
501	                        yield ","
502	                        # accumulate the partial thinking 
503	                        thinking += chunk.message.thinking
504	                    elif chunk.message.content:
505	                        if in_thinking:
506	                          in_thinking = False
507	                        # accumulate the partial content
508	                        content += chunk.message.content
509	                        yield json.dumps({'type':'response','content':chunk.message.content})
510	                        yield ","
511	                    if chunk.message.tool_calls:
512	                        print(chunk.message.tool_calls)
513	                        tool_calls.extend(chunk.message.tool_calls)
514	                        
515	                
516	                if in_thinking:
517	                          in_thinking = False
518	                if tool_calls:
519	                    # Build properly formatted tool_calls for storage
520	                    formatted_tool_calls = []
521	                    for tc in tool_calls:
522	                        if hasattr(tc, 'function'):  # Ollama ToolCall object
523	                            formatted_tool_calls.append({
524	                                "function": {
525	                                    "name": tc.function.name,
526	                                    "arguments": tc.function.arguments
527	                                }
528	                            })
529	                        elif isinstance(tc, dict):
530	                            # Handle dict case (sometimes happens)
531	                            if "function" not in tc:
532	                                formatted_tool_calls.append({
533	                                    "function": {
534	                                        "name": tc.get("name") or tc.get("function", {}).get("name"),
535	                                        "arguments": tc.get("arguments") or tc.get("function", {}).get("arguments", {})
536	                                    }
537	                                })
538	                            else:
539	                                formatted_tool_calls.append(tc)
540	                    assistant_msg = {
541	                        "role": "assistant",
542	                        "content": content or "",
543	                        "tool_calls": formatted_tool_calls,
544	                    }
545	                    global_messages[chatid].append(assistant_msg)
546	                    for tc in formatted_tool_calls:
547	                        fn = tc["function"]["name"]
548	                        args = tc["function"]["arguments"]
549	                        guard.add(fn)
550	
551	                        if guard.should_stop():
552	                            yield json.dumps({'type':'stop','content':'loop detected'})
553	                            yield ","
554	                            break   
555	                        if fn in available_functions:
556	                            yield json.dumps({'type':'tool','content':fn})
557	                            yield ","
558	                            final_result = ""
559	                            result = available_functions[fn](**args)
560	                            print(result)
561	                            if isinstance(result, types.GeneratorType):
562	                                for chunk in result:
563	                                    yield json.dumps({'type':'tool','content':chunk})
564	                                    yield ","
565	                                result = "sucess. agent did stuff"
566	                            else:
567	                                yield json.dumps({'type':'tool','content':str(result)})
568	                                yield ","
569	
570	                            if isinstance(result, dict) and result.get("status") == "ok" and "image" in result:
571	                                global_messages[chatid].append({
572	                                    "role": "tool",
573	                                    "content": f"the image will be sent by user in a second",
574	                                    "tool_name": fn,
575	                                })
576	                                global_messages[chatid].append({
577	                                    "role": "user",
578	                                    "content": f"here is your image",
579	                                    "images": [result["path"]],
580	                                })
581	                            else:
582	                                global_messages[chatid].append({
583	                                    "role": "tool",
584	                                    "tool_name": fn,
585	                                    "content": str(result)
586	                                })
587	
588	                    # Loop again so model can respond to tool result
589	                    continue
590	               
591	                    
592	                # append the accumulated fields to the messages for the next request
593	                global_messages[chatid].append({"role": "assistant", "content": content})
594	                break
595	            
596	            save(global_messages)
597	        except GeneratorExit:
598	            logger.warning(f"[{chatid}] GeneratorExit (client disconnected)")
599	
600	        except Exception as e:
601	            logger.error(f"[{chatid}] Fatal generate() error: {e}")
602	            logger.error(traceback.format_exc())
603	
604	            yield f"\n[FATAL ERROR] {e}"
605	
606	        finally:
607	            yield "]"
608	            logger.info(f"[{chatid}] generate() cleanup reached")
609	    return Response(generate(),mimetype="text/html")
610	        
611	@app.route("/",methods=["GET"])
612	def index():
613	    with open("test.html","r", encoding="utf-8") as r:
614	        index = r.read()
615	    index = index.replace("{computer_username_uuid_827392}",username_computer)
616	    return Response(index, mimetype="text/html; charset=utf-8")
617	
618	@app.route("/vc", methods=["GET"])
619	def vc_index():
620	    with open("vc.html", "r", encoding="utf-8") as r:
621	        page = r.read()
622	    return Response(page, mimetype="text/html; charset=utf-8")
623	
624	@app.route("/new",methods=["GET"])
625	def new():
626	    return str(len(global_messages))
627	if __name__ == "__main__":
628	    app.run(debug=False, use_reloader=False)
629	    
630	
631	