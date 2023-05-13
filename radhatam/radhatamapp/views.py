from django.shortcuts import render, HttpResponseRedirect, reverse, HttpResponse
from django.contrib import messages
from .forms import UploadFileForm, UploadFileDataForm, DerivedColumnForm
import pandas as pd
import pygwalker as pyg
from io import StringIO
import logging
from .models import Entity, Field, DATA_TYPES, SQL_OP_TYPES, FunctionMeta, ArgumentMeta, DerivedFieldArgument, FieldFilter
from django.db import connection
from django.conf import settings
import psycopg2
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)
# Create your views here.

PG_NAME = settings.DATABASES['default']['NAME']
PG_USER = settings.DATABASES['default']['USER']
PG_PWD = settings.DATABASES['default']['PASSWORD']
PG_HOST = settings.DATABASES['default']['HOST']
PG_PORT  = settings.DATABASES['default']['PORT']


conn = psycopg2.connect(dbname=PG_NAME, user=PG_USER, password=PG_PWD,host=PG_HOST,port=PG_PORT)
engine = create_engine(f"postgresql+psycopg2://{PG_USER}:{PG_PWD}@{PG_HOST}/{PG_NAME}")

# sql = "with cte_0 as ( select scripname, market, outlook, growwportfolio_file_name, pe, code, low, close, last, prevclose, no_trades, no_of_shrs, sc_name, net_turnov, sc_group, sc_type, tdcloindi, bhavcopy_file_name, sc_code, open, high from growwportfolio left join bhavcopy on growwportfolio.code = bhavcopy.sc_code ), cte_1 as ( select *, convert_str_to_date(bhavcopy_file_name) as trade_date from cte_0), cte_2 as ( select *, avg(close) over(partition by code order by trade_date asc rows between 200 preceding and current row) as sma200, rsi_sma(close) over(partition by code order by trade_date asc rows between 14 preceding and current row) as rsi_sma_14 from cte_1) , cte_3 as ( select *, RANK() OVER (PARTITION BY code ORDER BY trade_date desc) AS rnk from cte_2 ) select distinct * from cte_3 where outlook = 'LONGTERM' and close < sma200 and rsi_sma_14 < 30 and pe < 22 order by trade_date desc"
# sql = "with cte_0 as ( select low,close,last,prevclose,no_trades,no_of_shrs,sc_name,net_turnov,sc_group,sc_type,tdcloindi,bhavcopy_file_name,sc_code,open,high from bhavcopy) select * from cte_0"
def index(request):
    # cur = conn.cursor()
    # cur.execute(sql)
    # rs = cur.fetchall()
    # print(rs[0])
   
    entities = Entity.objects.all()
    return render(request, 'radhatamapp/index.html', context={'entities': entities})


def datastructure(request, action, id):
    data = {}
    entity = None
    fields = None
    if id:
        entity = Entity.objects.get(id=id)
        fields = Field.objects.filter(entity__id=id)
    if "GET" == request.method:        
        functions_calculated_meta = FunctionMeta.objects.filter(type='GENERATED')
        print(functions_calculated_meta)
        form = UploadFileForm()
        dataupload_form = UploadFileDataForm()
        entities = Entity.objects.exclude(id=id).all()
        return render(request, "radhatamapp/datastructure.html", context={'form': form, 'entity': entity, 'entities': entities, 'fields': fields, 'dtypes': DATA_TYPES, 'dataupload_form': dataupload_form,'functions_calculated_meta':functions_calculated_meta})
    # if not GET, then proceed
    if action == 'create':
        try:
            name = request.POST['name']
            csv_file = request.FILES["csv_file"]

            file_data = csv_file.read().decode("utf-8")
           
            cols = StringIO(file_data).readlines()[0].split(',')
      
            if id == 0:
                Entity.objects.filter(name=name).delete()
            entity = Entity.objects.create(name=name)
            entity.save()
            for col in cols:
                name = col.replace('.', '').replace(
                    '-', '_').replace("'", "").replace('"', '').replace(' ', '_').lower()
                Field.objects.create(
                    actual_name=col, name=name, entity=entity).save()
            # create an additinal file_name columnf
            Field.objects.create(
                actual_name=f'{entity.name}_file_name',
                name=f'{entity.name}_file_name', entity=entity).save()
            return HttpResponseRedirect(f'/datastructure/display/{entity.id}')
        # return HttpResponseRedirect(reverse("radhatamapp:create_entity"))

        except Exception as e:
            logging.getLogger("error_logger").error(
                "Unable to upload file. "+repr(e))
            messages.error(request, "Unable to upload file. "+repr(e))
    
    
    if action == 'add_calculated_field':
        derived_field_name = request.POST['derived_field_name']
        function_id = request.POST['function_id']
        

        function = FunctionMeta.objects.get(id=function_id)
        arguments_meta = ArgumentMeta.objects.filter(
            function__id=function_id)
        provided_argument = []
        for arg in arguments_meta:
            val = request.POST[arg.name]
            provided_argument.append(
                {"name": arg.name, "value": val, "type": arg.type})

        # argument_type = models.CharField(max_length=30, null=True)
        # create the derived field
        # field_level = get_level_of_fields(entity.id)
        derived_field = Field.objects.create(
            actual_name=derived_field_name, name=derived_field_name, entity=entity, type='CALCULATED', datatype=function.return_type, derived_level=0, function=function)
        derived_field.save()
        for parg in provided_argument:
            DerivedFieldArgument.objects.create(
                field=derived_field, argument_name=parg['name'], argument_value=parg['value'], argument_type=parg['type']).save()
        html = f'<span class="badge text-bg-primary">{function.name}</span>'
        return HttpResponse(html)

    if action == 'create_table':
        entity = Entity.objects.get(id=id)
        fields = Field.objects.filter(entity__id=id)
        sql = f"create table if not exists {entity.name}("

        for field in fields:
            if field.type == 'CALCULATED':
                function_meta = field.function
                derived_field_arguments = DerivedFieldArgument.objects.filter(
                    field=field.id)
                derived_values = {
                    d.argument_name: d.argument_value for d in derived_field_arguments}
                derived_values['name'] = field.name
                derived_function_sql = function_meta.return_sql.format(
                    **derived_values)

                sql += f"{field.name} {field.datatype} GENERATED ALWAYS AS ({derived_function_sql}) STORED,"
            elif field.type == 'DERIVED':
                pass
            else:
                sql += f"{field.name} {field.datatype},"

        sql = f"{sql[:-1]})"
        print(sql)
        execute_raw_query(f"drop table if exists {entity.name}")
        print(entity.name, ' DR')
        execute_raw_query(sql)
    if action == 'uploaddata':
        try:
            csv_files = request.FILES.getlist('csv_file')
            print(csv_files)

            entity = Entity.objects.get(id=id)
            fields = Field.objects.filter(entity__id=id)

            for csv_file in csv_files:
                print(csv_file)
                file_data = csv_file.read().decode("utf-8")
                file = StringIO(file_data).readlines()
                cols = file[0].split(',')
                print("============================================-")
                columns = []
                for col in cols:
                    name = replace_clean(col).lower()
                    columns.append(name)

                columns.append(f'{entity.name}_file_name')

                sql_cols = f"({(',').join(columns)})"
                for line in file[1:]:
                    # next(line)
                    vals = line.split(',')
                    field_sql = ''

                    for i, c in enumerate(vals):
                        if c.isdecimal() or c.isdigit() or c.isnumeric() or c.replace('.', '', 1).isdigit():
                            field_sql += f"{c},"
                        else:
                            c = c.replace("'", "")
                            field_sql += f"'{c}',"

                    field_sql = f"{field_sql}'{csv_file.name}'"
                    sql = f"insert into {entity.name} {sql_cols} values({field_sql})"
                    execute_raw_query(sql)
                    # break

            
        # return HttpResponseRedirect(reverse("radhatamapp:create_entity"))

        except Exception as e:
            logging.getLogger("error_logger").error(
                "Unable to upload file. "+repr(e))
            messages.error(request, "Unable to upload file. "+repr(e))
        return HttpResponseRedirect(f'/datastructure/display/{id}')
    if action == 'add_child':
        print(request.POST)
        if request.POST['child_entity_id'] and not request.POST['child_field_id']:
            child_entity_name = request.POST['child_entity_id']
            entity = Entity.objects.get(id=child_entity_name)
            fields = Field.objects.filter(entity__id=entity.id)
            html = '<option></option>'
            for field in fields:
                html += f"<option value='{field.id}'>{field.name}</option>"
            return HttpResponse(html)
        else:
            parent_field_id = request.POST['parent_field_id']
            child_entity_id = request.POST['child_entity_id']
            child_field_id = request.POST['child_field_id']
            parent_field = Field.objects.get(id=parent_field_id)
            parent_field.child_entity_id = child_entity_id
            parent_field.child_field_id = child_field_id
            parent_field.save()

            # field = Field.objects.get(id=parent)
        return HttpResponse("done")
    return HttpResponseRedirect(reverse("radhatamapp:datastructure", kwargs={'action': 'display', 'id': id}))


def edit_fieldtype(request, id):
    if "POST" == request.method:
        print(id, request.POST)
        field_name = None
        dtype = None
        for k, v in request.POST.items():
            field_name = k
            dtype = v

        field = Field.objects.get(id=id)
        field.datatype = dtype
        field.save()
        return HttpResponse("<option>selected</option>")


def dataprep(request, action, id):
    print("***********************************")
    print(action, id)
    print("***********************************")
    data = {}
    entity = Entity.objects.get(id=id)
    if "GET" == request.method:
      

        fields = Field.objects.filter(
            entity=entity, derived_level__gte=1).order_by('derived_level')
        print(fields)

        data_sql = generate_cte_sql(id)
        create_meta_table(entity.name, data_sql)

        full_data_sql = generate_action_sql(data_sql, id, action)
        data, col_names = fetch_raw_query(full_data_sql)
        entity_columns_meta = get_table_columns(f"{entity.name}_meta")
        level_field = get_level_of_fields(id)
        available_functions = FunctionMeta.objects.filter().exclude(type='GENERATED')
        print(available_functions,'===========')
        # functions_viz_meta = FunctionMeta.objects.filter(type='VISUALIZATION')
        # functions_ds_meta = FunctionMeta.objects.filter(type='DATASCIENCE')

        filters = FieldFilter.objects.filter(entity=entity)

        if action == 'apply_table_filter':
            print(request.GET)
            fieldFilters = FieldFilter.objects.filter(entity=entity)
            new_filter_col = request.GET.get('filter_col_0')
            new_filter_op = request.GET.get('filter_op_0')
            new_filter_val = request.GET.get('filter_val_0')
            print(new_filter_col, new_filter_op, new_filter_val)

            field_filter_array = []
            if new_filter_col and new_filter_op and new_filter_val:
                field_filter_array = [{'filter_col': new_filter_col,
                                       'filter_op': new_filter_op, 'filter_val': new_filter_val}]

            for fieldFilter in fieldFilters:
                new_filter_col = request.GET.get(
                    f'filter_col_{fieldFilter.id}')
                new_filter_op = request.GET.get(f'filter_op_{fieldFilter.id}')
                new_filter_val = request.GET.get(
                    f'filter_val_{fieldFilter.id}')
                if new_filter_col and new_filter_op and new_filter_val:
                    field_filter_array.append(
                        {'filter_col': new_filter_col, 'filter_op': new_filter_op, 'filter_val': new_filter_val})
            print(field_filter_array)

            # Delete previous objects
            if (new_filter_col and new_filter_op and new_filter_val) or field_filter_array:
                FieldFilter.objects.filter(entity=entity).delete()

            # # create all new
            for field_filter in field_filter_array:
                FieldFilter.objects.create(
                    entity=entity, filter_col=field_filter['filter_col'], filter_op=field_filter['filter_op'], filter_val=field_filter['filter_val'])
            return HttpResponseRedirect(f'/dataprep/display/{entity.id}')
        return render(request, "radhatamapp/dataprep.html",
                      context={'entity': entity, 'fields': fields, 'data': data,
                               'col_names': col_names, 'level_field': level_field+1,
                               'available_functions': available_functions,
                               'filters': filters,
                               'entity_columns_meta': entity_columns_meta,
                               'action': action,
                               })

    if action == 'delete_filter':
        field_filter_id = request.GET.get('filter_id')
        FieldFilter.objects.get(id=field_filter_id).delete()
        return HttpResponse('deleted')

    if action == 'apply_filter':
        print(request.POST)
        fieldFilters = FieldFilter.objects.filter(entity=entity)
        new_filter_col = request.POST['filter_col_0']
        new_filter_op = request.POST['filter_op_0']
        new_filter_val = request.POST['filter_val_0']
        print(new_filter_col, new_filter_op, new_filter_val)
        field_filter_array = [{'filter_col': new_filter_col,
                               'filter_op': new_filter_op, 'filter_val': new_filter_val}]

        for fieldFilter in fieldFilters:
            new_filter_col = request.POST[f'filter_col_{fieldFilter.id}']
            new_filter_op = request.POST[f'filter_op_{fieldFilter.id}']
            new_filter_val = request.POST[f'filter_val_{fieldFilter.id}']
            field_filter_array.append(
                {'filter_col': new_filter_col, 'filter_op': new_filter_op, 'filter_val': new_filter_val})
        print(field_filter_array)
        # Delete previous objects
        # FieldFilter.objects.filter(entity=entity).delete()

        # # create all new
        for field_filter in field_filter_array:
            FieldFilter.objects.create(
                entity=entity, filter_col=field_filter['filter_col'], filter_op=field_filter['filter_op'], filter_val=field_filter['filter_val'])
        return HttpResponse('ok')
    if action == 'get_function_params':
        try:
            function_id = request.POST['function_id']
            function_meta = FunctionMeta.objects.get(id=function_id)
            arguments_meta = ArgumentMeta.objects.filter(
                function__id=function_id)
            entity_columns_meta = get_table_columns(f"{entity.name}_meta")
            entity_columns_names = [col['name'] for col in entity_columns_meta]
            html = '<label>Field Name</label><input type="text" name="derived_field_name"/>'
            for arg in arguments_meta:
                html += f'<label>{arg.name}</label>'
                if arg.type == 'COLUMN':
                    html += f'<select name={arg.name}>'
                    for entity_col in entity_columns_names:
                        html += f'<option value="{entity_col}">{entity_col}</option>'
                    html += '</select>'
                else:
                    html += f'<input type="{arg.type}" name="{arg.name}"/>'
            return HttpResponse(html)
        except Exception as e:
            logging.getLogger("error_logger").error(
                "Unable to upload file. "+repr(e))
            messages.error(request, "Unable to upload file. "+repr(e))

    if action == 'add_derived_field':
        derived_field_name = request.POST['derived_field_name']
        function_id = request.POST['function_id']
        level_field = request.POST['level_field']

        function = FunctionMeta.objects.get(id=function_id)
        arguments_meta = ArgumentMeta.objects.filter(
            function__id=function_id)
        provided_argument = []
        for arg in arguments_meta:
            val = request.POST[arg.name]
            provided_argument.append(
                {"name": arg.name, "value": val, "type": arg.type})

        # argument_type = models.CharField(max_length=30, null=True)
        # create the derived field
        # field_level = get_level_of_fields(entity.id)
        derived_field = Field.objects.create(
            actual_name=derived_field_name, name=derived_field_name, entity=entity, type='DERIVED', datatype=function.return_type ,derived_level=level_field, function=function)
        derived_field.save()
        for parg in provided_argument:
            DerivedFieldArgument.objects.create(
                field=derived_field, argument_name=parg['name'], argument_value=parg['value'], argument_type=parg['type']).save()
        html = f'<span class="badge text-bg-primary">{function.name}</span>'
        return HttpResponse(html)


def dataviz(request, action, id):
    print("***********************************")
    print(action, id)
    print("***********************************")
    data = {}
    entity = Entity.objects.get(id=id)
    if "GET" == request.method:
      

        fields = Field.objects.filter(
            entity=entity, derived_level__gte=1).order_by('derived_level')
        print(fields)

        data_sql = generate_cte_sql(id)
        create_meta_table(entity.name, data_sql)

        full_data_sql = generate_action_sql(data_sql, id, action)
        data, col_names = fetch_raw_query(full_data_sql)
        entity_columns_meta = get_table_columns(f"{entity.name}_meta")
        level_field = get_level_of_fields(id)
        available_functions = FunctionMeta.objects.filter().exclude(type='GENERATED')
        print(available_functions,'===========')
        # functions_viz_meta = FunctionMeta.objects.filter(type='VISUALIZATION')
        # functions_ds_meta = FunctionMeta.objects.filter(type='DATASCIENCE')

        filters = FieldFilter.objects.filter(entity=entity)

        if action == 'apply_table_filter':
            print(request.GET)
            fieldFilters = FieldFilter.objects.filter(entity=entity)
            new_filter_col = request.GET.get('filter_col_0')
            new_filter_op = request.GET.get('filter_op_0')
            new_filter_val = request.GET.get('filter_val_0')
            print(new_filter_col, new_filter_op, new_filter_val)

            field_filter_array = []
            if new_filter_col and new_filter_op and new_filter_val:
                field_filter_array = [{'filter_col': new_filter_col,
                                       'filter_op': new_filter_op, 'filter_val': new_filter_val}]

            for fieldFilter in fieldFilters:
                new_filter_col = request.GET.get(
                    f'filter_col_{fieldFilter.id}')
                new_filter_op = request.GET.get(f'filter_op_{fieldFilter.id}')
                new_filter_val = request.GET.get(
                    f'filter_val_{fieldFilter.id}')
                if new_filter_col and new_filter_op and new_filter_val:
                    field_filter_array.append(
                        {'filter_col': new_filter_col, 'filter_op': new_filter_op, 'filter_val': new_filter_val})
            print(field_filter_array)

            # Delete previous objects
            if (new_filter_col and new_filter_op and new_filter_val) or field_filter_array:
                FieldFilter.objects.filter(entity=entity).delete()

            # # create all new
            for field_filter in field_filter_array:
                FieldFilter.objects.create(
                    entity=entity, filter_col=field_filter['filter_col'], filter_op=field_filter['filter_op'], filter_val=field_filter['filter_val'])
            return HttpResponseRedirect(f'/dataviz/display/{entity.id}')
        # PG Walker
        eda = None
        if action == 'visualize':
            # df = pd.read_csv('C:\\3Projects\\newstockup\\indexes\\sensex_historical_gen.csv',parse_dates=['Date'])
            print("=========VISUALIZE SQL ==========================")
            print(full_data_sql)
            # full_data_sql = full_data_sql +  " where trade_date = '2023-05-09'"
            df = pd.read_sql(full_data_sql, engine)

            eda  = pyg.walk(df,hiddenDataSourceConfig=True, vegaTheme='vega',return_html=True)
        return render(request, "radhatamapp/dataviz.html",
                      context={'entity': entity, 'fields': fields, 'data': data,
                               'col_names': col_names, 'level_field': level_field+1,
                               'available_functions': available_functions,
                               'filters': filters,
                               'entity_columns_meta': entity_columns_meta,
                               'action': action,
                               'eda':eda
                               })

    if action == 'delete_filter':
        field_filter_id = request.GET.get('filter_id')
        FieldFilter.objects.get(id=field_filter_id).delete()
        return HttpResponse('deleted')

    if action == 'apply_filter':
        print(request.POST)
        fieldFilters = FieldFilter.objects.filter(entity=entity)
        new_filter_col = request.POST['filter_col_0']
        new_filter_op = request.POST['filter_op_0']
        new_filter_val = request.POST['filter_val_0']
        print(new_filter_col, new_filter_op, new_filter_val)
        field_filter_array = [{'filter_col': new_filter_col,
                               'filter_op': new_filter_op, 'filter_val': new_filter_val}]

        for fieldFilter in fieldFilters:
            new_filter_col = request.POST[f'filter_col_{fieldFilter.id}']
            new_filter_op = request.POST[f'filter_op_{fieldFilter.id}']
            new_filter_val = request.POST[f'filter_val_{fieldFilter.id}']
            field_filter_array.append(
                {'filter_col': new_filter_col, 'filter_op': new_filter_op, 'filter_val': new_filter_val})
        print(field_filter_array)
        # Delete previous objects
        # FieldFilter.objects.filter(entity=entity).delete()

        # # create all new
        for field_filter in field_filter_array:
            FieldFilter.objects.create(
                entity=entity, filter_col=field_filter['filter_col'], filter_op=field_filter['filter_op'], filter_val=field_filter['filter_val'])
        return HttpResponse('ok')
    if action == 'get_function_params':
        try:
            function_id = request.POST['function_id']
            function_meta = FunctionMeta.objects.get(id=function_id)
            arguments_meta = ArgumentMeta.objects.filter(
                function__id=function_id)
            entity_columns_meta = get_table_columns(f"{entity.name}_meta")
            entity_columns_names = [col['name'] for col in entity_columns_meta]
            html = '<label>Field Name</label><input type="text" name="derived_field_name"/>'
            for arg in arguments_meta:
                html += f'<label>{arg.name}</label>'
                if arg.type == 'COLUMN':
                    html += f'<select name={arg.name}>'
                    for entity_col in entity_columns_names:
                        html += f'<option value="{entity_col}">{entity_col}</option>'
                    html += '</select>'
                else:
                    html += f'<input type="{arg.type}" name="{arg.name}"/>'
            return HttpResponse(html)
        except Exception as e:
            logging.getLogger("error_logger").error(
                "Unable to upload file. "+repr(e))
            messages.error(request, "Unable to upload file. "+repr(e))

    if action == 'add_derived_field':
        derived_field_name = request.POST['derived_field_name']
        function_id = request.POST['function_id']
        level_field = request.POST['level_field']

        function = FunctionMeta.objects.get(id=function_id)
        arguments_meta = ArgumentMeta.objects.filter(
            function__id=function_id)
        provided_argument = []
        for arg in arguments_meta:
            val = request.POST[arg.name]
            provided_argument.append(
                {"name": arg.name, "value": val, "type": arg.type})

        # argument_type = models.CharField(max_length=30, null=True)
        # create the derived field
        # field_level = get_level_of_fields(entity.id)
        derived_field = Field.objects.create(
            actual_name=derived_field_name, name=derived_field_name, entity=entity, type='DERIVED', datatype=function.return_type ,derived_level=level_field, function=function)
        derived_field.save()
        for parg in provided_argument:
            DerivedFieldArgument.objects.create(
                field=derived_field, argument_name=parg['name'], argument_value=parg['value'], argument_type=parg['type']).save()
        html = f'<span class="badge text-bg-primary">{function.name}</span>'
        return HttpResponse(html)


def dataalerts(request,action,id):
    return render(request, 'radhatamapp/dataalerts.html', context={'entities': {}})

def handle_uploaded_file(f):
    with open('some/file/name.txt', 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def upload_csv(request):
    data = {}
    if "GET" == request.method:
        return render(request, "myapp/upload_csv.html", data)
    # if not GET, then proceed
    try:
        csv_file = request.FILES["csv_file"]
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File is not CSV type')
            return HttpResponseRedirect(reverse("myapp:upload_csv"))
    # if file is too large, return
        if csv_file.multiple_chunks():
            messages.error(request, "Uploaded file is too big (%.2f MB)." % (
                csv_file.size/(1000*1000),))
            return HttpResponseRedirect(reverse("myapp:upload_csv"))

        file_data = csv_file.read().decode("utf-8")

        lines = file_data.split("\n")
        # loop over the lines and save them in db. If error , store as string and then display
        for line in lines:
            fields = line.split(",")
            data_dict = {}
            data_dict["name"] = fields[0]
            data_dict["start_date_time"] = fields[1]
            data_dict["end_date_time"] = fields[2]
            data_dict["notes"] = fields[3]
            try:
                form = EventsForm(data_dict)
                if form.is_valid():
                    form.save()
                else:
                    logging.getLogger("error_logger").error(
                        form.errors.as_json())
            except Exception as e:
                logging.getLogger("error_logger").error(repr(e))
                pass

    except Exception as e:
        logging.getLogger("error_logger").error(
            "Unable to upload file. "+repr(e))
        messages.error(request, "Unable to upload file. "+repr(e))

    return HttpResponseRedirect(reverse("myapp:upload_csv"))


def execute_raw_query(sql):
    # print("============execute_raw_query=====================")
    # print(sql)
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
    except Exception as e:
        print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        print("Exception in execute raw query")
        print(e)
        print(sql)


def fetch_raw_query(sql):
    print("============fetch_raw_query=====================")
    print(sql)
    with connection.cursor() as cursor:
        cursor.execute(sql)
        col_names = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

    return rows, col_names


def get_level_of_fields(id):
    top_level = Field.objects.filter(entity__id=id).order_by(
        '-derived_level').values_list('derived_level')
    print(top_level[0])
    return top_level[0][0]


def generate_cte_sql(id, action=None):
    entity = Entity.objects.get(id=id)

    field_level = get_level_of_fields(id) + 1

    field_filter = FieldFilter.objects.filter(entity=entity)
    entity_columns_meta = get_table_columns(f"{entity.name}_meta")

    data_sql = None
    for i in range(field_level):
        if i == 0:
            all_child_entity_fields = None
            child_entity = None
            field_with_child = None
            child_field = None

            fields = None

            fields = Field.objects.filter(entity__id=id, derived_level=i)
            for field in fields:
                if field.child_entity_id and field.child_field_id:
                    field_with_child = field
                    child_entity = Entity.objects.get(id=field.child_entity_id)
                    child_field = Field.objects.get(id=field.child_field_id)
                    all_child_entity_fields = Field.objects.filter(
                        entity__id=field.child_entity_id)
            if all_child_entity_fields:
                f = fields.union(all_child_entity_fields,
                                 all=True).values_list('name', flat=True)
                f = [replace_clean(c) for c in f]
                fields_sql = ",".join(f)
                data_sql = f" with cte_{i} as ( select {fields_sql} from {entity.name} left join {child_entity.name} on {entity}.{field_with_child.name} = {child_entity.name}.{child_field.name} "
            else:
                f = fields.values_list('name', flat=True)
                f = [replace_clean(c) for c in f]
                fields_sql = ",".join(f)
                data_sql = f"with cte_{i} as ( select {fields_sql} from {entity.name}"

        else:
            # All fields from level 1 are derived
            all_child_entity_fields = None
            child_entity = None
            field_with_child = None
            child_field = None

            fields = None

            fields = Field.objects.filter(entity__id=id, derived_level=i).exclude(type = 'CALCULATION')
            data_sql += f'),cte_{i} as ( select *,'
            for field in fields:
                function_meta = field.function

                derived_field_arguments = DerivedFieldArgument.objects.filter(
                    field=field.id)

                derived_values = {
                    d.argument_name: d.argument_value for d in derived_field_arguments}
                derived_values['name'] = field.name
                derived_function_sql = function_meta.return_sql.format(**derived_values)

                data_sql += f'{derived_function_sql},'

            data_sql = f'{data_sql[:-1]} from cte_{i-1}'

        

    # rank_sql = f"cte_3 as (select *,RANK() OVER (PARTITION BY code ORDER BY trade_date desc) AS rank from cte_2"
    data_sql += f") select * from cte_{field_level-1}"
    return data_sql


def generate_action_sql(sql, id, action=None):
    entity = Entity.objects.get(id=id)

    field_filter = FieldFilter.objects.filter(entity=entity)
    entity_columns_meta = get_table_columns(f"{entity.name}_meta")
    print(entity_columns_meta)

    where_list = ''
    for filter in field_filter:
        # Get type, it will determine whether to wrap in '
        col_type = None
        for col_meta in entity_columns_meta:
            print("+_+_+_+_+_+_+_+_+_+_+_+_+_+_")
            print(filter.filter_col, col_meta)
            if filter.filter_col == col_meta['name']:
                col_type = col_meta['type']

        # Based on type identity
   
        print(col_type)
        if col_type and col_type.lower() in ['text', 'date']:
            where_list += f" {filter.filter_col} {SQL_OP_TYPES[filter.filter_op]} '{filter.filter_val}' and "
        else:
            where_list += f" {filter.filter_col} {SQL_OP_TYPES[filter.filter_op]} {filter.filter_val} and "
   
    where_list = where_list[:-4]
    print(where_list)

   
    if where_list and (action == 'display' or action  == 'visualize'):
        sql += f" where {where_list}"
    else:
        sql += f" limit 500 "

    return sql


def replace_clean(str):
    return str.replace('.', '').replace('-', '_').replace("'", "").replace('"', '').replace(' ', '_').replace('\n', '').replace('\r', '').replace('\r\n', '')


def create_meta_table(entity_name, data_sql):
    sql = f"drop table if exists {entity_name}_meta"
    execute_raw_query(sql)

    sql = f"create table {entity_name}_meta as {data_sql} limit 1"
    execute_raw_query(sql)


def get_table_columns(tname):
    sql = f'''
        SELECT column_name, data_type 
        FROM information_schema.columns
        WHERE table_name = '{tname}' AND table_schema = 'public';
    '''
    table_cols = fetch_raw_query(sql)
    cols = []
    for col in table_cols[0]:
        cols.append({"name": col[0], 'type': col[1]})
    return cols
