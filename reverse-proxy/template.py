import os
import json
import yaml
from jinja2 import Environment, FileSystemLoader, Template
from utils import concat_abis, load_json_file, load_yaml_file, write_yaml_file, write_json_file, write_text_file

J2_ENV = Environment(loader=FileSystemLoader(''), trim_blocks=True)
wd = os.getcwd()

def yaml_from_abi():
	try:
		data = concat_abis(None,None,"list")
		inputs = []
		inputs.append({'name':'id','value':'PrimaryKey(int, auto=True)'})
		inputs.append({'name':'xquery_chain_name','value':'Required(str)'})
		inputs.append({'name':'xquery_query_name','value':'Required(str)'})
		inputs.append({'name':'xquery_timestamp','value':'Required(int)'})
		inputs.append({'name':'xquery_tx_hash','value':'Required(str)'})
		inputs.append({'name':'xquery_token0_name','value':'Optional(str)'})
		inputs.append({'name':'xquery_token0_symbol','value':'Optional(str)'})
		inputs.append({'name':'xquery_token0_decimals','value':'Optional(str)'})
		inputs.append({'name':'xquery_token1_name','value':'Optional(str)'})
		inputs.append({'name':'xquery_token1_symbol','value':'Optional(str)'})
		inputs.append({'name':'xquery_token1_decimals','value':'Optional(str)'})
		inputs.append({'name':'xquery_side','value':'Optional(str)'})
		inputs.append({'name':'xquery_address_filter','value':'Optional(str)'})
		inputs.append({'name':'xquery_blocknumber','value':'Optional(int)'})
		for i in data:
			if i['type'].lower() == 'event':
				for k in i['inputs']:
					name = k['name']
					val = 'Optional(str)'
					if name == '':
						name = 'xquery_none'
					if '_' not in name:
						name = 'xquery_'+name
					inputs.append({'name':name.lower(),'value':val})
		inputs = list({v['name']:v for v in inputs}.values())
		yamldata = [{"classes":[{"name":"XQuery","attributes":inputs}]}]
		write_yaml_file(yamldata,"schema.yaml")
		return yamldata
	except Exception as e:
		print(e)

def process_template(data):
	custom_template = J2_ENV.get_template('templates/template.j2')
	rendered_data = custom_template.render(data)
	with open('/etc/nginx/nginx.conf', "w") as fname:
		fname.write(rendered_data)

def gen_data_for_template(abis):
	final_data = {}
	final_data['chains'] = []
	env = os.environ.__dict__['_data']
	entries = list(env)
	d = []
	hasura_port = ''
	hasura_ip = ''
	chain_endpoint = ''
	for e in entries:
		e = e.decode('utf-8')
		if 'CHAIN_ENDPOINT' in e:
			chain_endpoint = env[str.encode(e)].decode('utf-8')
		elif 'CHAIN_HASURA_PORT' in e:
			hasura_port = env[str.encode(e)].decode('utf-8')
		elif 'CHAIN_HASURA' in e:
			hasura_ip = env[str.encode(e)].decode('utf-8')
	final_data['endpoint'] = chain_endpoint
	final_data['hasura_ip'] = hasura_ip
	final_data['hasura_port'] = hasura_port
	final_data['chains'] = []
	for key, item in abis.items():
		for k, i in item.items():
			final_data['chains'].append({
				"name":key,
				"event":k
				})
	return final_data

def general_schema_text(data):
	text = ""
	for t in data[0]['classes'][0]['attributes']:
		text += f"  {t['name']}: {t['value'].split('(')[-1].split(',')[0].split(')')[0].capitalize()}!\n"
	final_text = """
type xquery {{
{text}
}}
""".format(text=text)
	write_text_file(final_text, "examples/schema.txt")
	print(final_text)

def query_text(data):
	for key, item in data.items():
		final_text = "query MyQuery {\n"
		chain_name = key
		for k, i in item.items():
			event_name = k
			final_text += """ xquery(where: {xquery_chain_name: {_eq: "CHAIN_NAME"}, xquery_query_name: {_eq: "EVENT_NAME"}})\n {\n""".replace("CHAIN_NAME", chain_name).replace("EVENT_NAME", event_name)
			for kk, ii in i.items():
				final_text += f"  {kk}\n"
			final_text += " }\n}"
		write_text_file(final_text, f"examples/{chain_name}_{event_name}.txt")
		print(final_text)
	
def help_text(query, data):
	endpoint = query['endpoint']
	text = "Hasura console\n\t"+"http://localhost:80/hasura/\n\n"
	text +="GraphQL endpoint\n\t"+ f"http://localhost:80{endpoint}/\n\n"
	text +="GraphQL endpoint\n\t"+ f"http://localhost:80/graphql/\n\n"
	text +="List available endpoints\n\t"+ f"http://localhost:80/help.txt\n\n"
	text +="GraphQL data types\n\t"+ f"http://localhost:80/help/schema.txt\n\n"
	for key, item in data.items():
		for k, i in item.items():
			text +=f"Query example for chain {key} and event {k}\n\t"+ f"http://localhost:80/help/{key}_{k}.txt\n\n"
	write_text_file(text, f"examples/help.txt")
	print(text)

if __name__ == "__main__":
	#gen schema
	_type = os.environ.get('SCHEMA','abi')
	wd = os.getcwd()
	data = yaml_from_abi()
	query = load_yaml_file("query.yaml")

	#load needed data
	#events with inputs
	abis = concat_abis(query, data, 'dict')
	help_text(query, abis)
	general_schema_text(data)
	query_text(abis)

	#write nginx from jinja2 template
	final_data = gen_data_for_template(abis)
	process_template(final_data)

	