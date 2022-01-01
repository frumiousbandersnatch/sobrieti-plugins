#!/usr/bin/env python
'''
A CLI to bucket
'''

import click
import store

@click.group("cli")
@click.pass_context
@click.option("-d", "--database", default=":memory:",
              help="Bucket sqlite3 database file")
def cli(ctx, database):
    ctx.obj = store.Bucket(database)

@cli.command("run")
@click.argument("command")
@click.argument("args", nargs=-1)
@click.pass_context
def run(ctx, command, args):
    '''
    Run a store.<command>(args)
    '''
    c = getattr(ctx.obj, command)
    
    pos = list()
    params = dict()
    for arg in args:
        if "=" in arg:
            k,v = arg.split("=",1)
            params[k] = v
        else:
            pos.append(arg)

    sargs = ','.join([f'"{a}"' for a in pos])
    skargs = ','.join([f'{k}="{v}"' for k,v in params.items()])
    print(f'{command}({sargs}, {skargs})')
    r = c(*pos, **params)
    print(r)

@cli.command("sql")
@click.argument("query", nargs=-1)
@click.pass_context
def sql(ctx, query):
    '''
    Execute arbitrary SQL on bucket database.
    '''
    got = ctx.obj.db.execute(' '.join(query)).fetchall()
    for one in got:
        print(one)

def main():
   cli(prog_name="bucket")
 
if __name__ == '__main__':
   main()


