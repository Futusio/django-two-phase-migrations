import sys
from importlib import import_module

from django.apps import apps
from django.core.management.base import CommandError, no_translations
from django.core.management.commands.migrate import Command
from django.core.management.sql import emit_post_migrate_signal, emit_pre_migrate_signal
from django.db import connections, connection, transaction
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import AmbiguityError
from django.db.migrations.state import ModelState, ProjectState
from django.utils.module_loading import module_has_submodule


class Command(Command):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        super().add_arguments(parser)
        # Blue-Green deployment arguments
        parser.add_argument(
            "--blue",
            action="store_true",
            dest="blue",
            help="Run in Blue deployment mode: execute _blue migrations and vanilla migrations (skip _green)",
        )
        parser.add_argument(
            "--green",
            action="store_true",
            dest="green",
            help="Run in Green deployment mode: execute _green migrations and vanilla migrations (skip _blue)",
        )

    @no_translations
    def handle(self, *args, **options):
        # Validate blue-green flags
        if options.get('blue') and options.get('green'):
            raise CommandError(
                "Cannot use --blue and --green flags together. "
                "Choose one deployment mode."
            )
        
        database = options["database"]
        if not options["skip_checks"]:
            self.check(databases=[database])

        self.verbosity = options["verbosity"]
        self.interactive = options["interactive"]

        # Import the 'management' module within each installed app, to register
        # dispatcher events.
        for app_config in apps.get_app_configs():
            if module_has_submodule(app_config.module, "management"):
                import_module(".management", app_config.name)

        # Get the database we're operating from
        connection = connections[database]

        # Hook for backends needing any database preparation
        connection.prepare_database()
        # Work out which apps have migrations and which do not
        executor = MigrationExecutor(connection, self.migration_progress_callback)

        # Raise an error if any migrations are applied before their dependencies.
        executor.loader.check_consistent_history(connection)

        # Before anything else, see if there's conflicting apps and drop out
        # hard if there are any
        conflicts = executor.loader.detect_conflicts()
        if conflicts:
            name_str = "; ".join(
                "%s in %s" % (", ".join(names), app) for app, names in conflicts.items()
            )
            raise CommandError(
                "Conflicting migrations detected; multiple leaf nodes in the "
                "migration graph: (%s).\nTo fix them run "
                "'python manage.py makemigrations --merge'" % name_str
            )

        # If they supplied command line arguments, work out what they mean.
        run_syncdb = options["run_syncdb"]
        target_app_labels_only = True
        if options["app_label"]:
            # Validate app_label.
            app_label = options["app_label"]
            try:
                apps.get_app_config(app_label)
            except LookupError as err:
                raise CommandError(str(err))
            if run_syncdb:
                if app_label in executor.loader.migrated_apps:
                    raise CommandError(
                        "Can't use run_syncdb with app '%s' as it has migrations."
                        % app_label
                    )
            elif app_label not in executor.loader.migrated_apps:
                raise CommandError("App '%s' does not have migrations." % app_label)

        if options["app_label"] and options["migration_name"]:
            migration_name = options["migration_name"]
            if migration_name == "zero":
                targets = [(app_label, None)]
            else:
                try:
                    migration = executor.loader.get_migration_by_prefix(
                        app_label, migration_name
                    )
                except AmbiguityError:
                    raise CommandError(
                        "More than one migration matches '%s' in app '%s'. "
                        "Please be more specific." % (migration_name, app_label)
                    )
                except KeyError:
                    raise CommandError(
                        "Cannot find a migration matching '%s' from app '%s'."
                        % (migration_name, app_label)
                    )
                target = (app_label, migration.name)
                # Partially applied squashed migrations are not included in the
                # graph, use the last replacement instead.
                if (
                    target not in executor.loader.graph.nodes
                    and target in executor.loader.replacements
                ):
                    incomplete_migration = executor.loader.replacements[target]
                    target = incomplete_migration.replaces[-1]
                targets = [target]
            target_app_labels_only = False
        elif options["app_label"]:
            targets = [
                key for key in executor.loader.graph.leaf_nodes() if key[0] == app_label
            ]
        else:
            targets = executor.loader.graph.leaf_nodes()
        if options["prune"]:
            if not options["app_label"]:
                raise CommandError(
                    "Migrations can be pruned only when an app is specified."
                )
            if self.verbosity > 0:
                self.stdout.write("Pruning migrations:", self.style.MIGRATE_HEADING)
            to_prune = set(executor.loader.applied_migrations) - set(
                executor.loader.disk_migrations
            )
            squashed_migrations_with_deleted_replaced_migrations = [
                migration_key
                for migration_key, migration_obj in executor.loader.replacements.items()
                if any(replaced in to_prune for replaced in migration_obj.replaces)
            ]
            if squashed_migrations_with_deleted_replaced_migrations:
                self.stdout.write(
                    self.style.NOTICE(
                        "  Cannot use --prune because the following squashed "
                        "migrations have their 'replaces' attributes and may not "
                        "be recorded as applied:"
                    )
                )
                for migration in squashed_migrations_with_deleted_replaced_migrations:
                    app, name = migration
                    self.stdout.write(f"    {app}.{name}")
                self.stdout.write(
                    self.style.NOTICE(
                        "  Re-run 'manage.py migrate' if they are not marked as "
                        "applied, and remove 'replaces' attributes in their "
                        "Migration classes."
                    )
                )
            else:
                to_prune = sorted(
                    migration for migration in to_prune if migration[0] == app_label
                )
                if to_prune:
                    for migration in to_prune:
                        app, name = migration
                        if self.verbosity > 0:
                            self.stdout.write(
                                self.style.MIGRATE_LABEL(f"  Pruning {app}.{name}"),
                                ending="",
                            )
                        executor.recorder.record_unapplied(app, name)
                        if self.verbosity > 0:
                            self.stdout.write(self.style.SUCCESS(" OK"))
                elif self.verbosity > 0:
                    self.stdout.write("  No migrations to prune.")

        plan = executor.migration_plan(targets)
        
        # Blue-Green deployment filtering
        if options['blue']:
            # Blue environment: run _blue migrations + vanilla migrations (without suffix)
            original_plan_count = len(plan)
            plan = [
                item for item in plan 
                if not item[0].name.endswith('_green')
            ]
            if self.verbosity >= 1 and original_plan_count != len(plan):
                filtered_count = original_plan_count - len(plan)
                self.stdout.write(
                    self.style.WARNING(
                        f"Blue deployment mode: skipping {filtered_count} green migration(s)"
                    )
                )
        elif options['green']:
            # Green environment: run _green migrations + vanilla migrations (without suffix)
            original_plan_count = len(plan)
            plan = [
                item for item in plan 
                if not item[0].name.endswith('_blue')
            ]
            if self.verbosity >= 1 and original_plan_count != len(plan):
                filtered_count = original_plan_count - len(plan)
                self.stdout.write(
                    self.style.WARNING(
                        f"Green deployment mode: skipping {filtered_count} blue migration(s)"
                    )
                )
        if options["plan"]:
            self.stdout.write("Planned operations:", self.style.MIGRATE_LABEL)
            if not plan:
                self.stdout.write("  No planned migration operations.")
            else:
                for migration, backwards in plan:
                    self.stdout.write(str(migration), self.style.MIGRATE_HEADING)
                    for operation in migration.operations:
                        message, is_error = self.describe_operation(
                            operation, backwards
                        )
                        style = self.style.WARNING if is_error else None
                        self.stdout.write("    " + message, style)
                if options["check_unapplied"]:
                    sys.exit(1)
            return
        if options["check_unapplied"]:
            if plan:
                sys.exit(1)
            return
        if options["prune"]:
            return

        # At this point, ignore run_syncdb if there aren't any apps to sync.
        run_syncdb = options["run_syncdb"] and executor.loader.unmigrated_apps
        # Print some useful info
        if self.verbosity >= 1:
            self.stdout.write(self.style.MIGRATE_HEADING("Operations to perform:"))
            if run_syncdb:
                if options["app_label"]:
                    self.stdout.write(
                        self.style.MIGRATE_LABEL(
                            "  Synchronize unmigrated app: %s" % app_label
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.MIGRATE_LABEL("  Synchronize unmigrated apps: ")
                        + (", ".join(sorted(executor.loader.unmigrated_apps)))
                    )
            if target_app_labels_only:
                self.stdout.write(
                    self.style.MIGRATE_LABEL("  Apply all migrations: ")
                    + (", ".join(sorted({a for a, n in targets})) or "(none)")
                )
            else:
                if targets[0][1] is None:
                    self.stdout.write(
                        self.style.MIGRATE_LABEL("  Unapply all migrations: ")
                        + str(targets[0][0])
                    )
                else:
                    self.stdout.write(
                        self.style.MIGRATE_LABEL("  Target specific migration: ")
                        + "%s, from %s" % (targets[0][1], targets[0][0])
                    )

        pre_migrate_state = executor._create_project_state(with_applied_migrations=True)
        pre_migrate_apps = pre_migrate_state.apps
        emit_pre_migrate_signal(
            self.verbosity,
            self.interactive,
            connection.alias,
            stdout=self.stdout,
            apps=pre_migrate_apps,
            plan=plan,
        )

        # Run the syncdb phase.
        if run_syncdb:
            if self.verbosity >= 1:
                self.stdout.write(
                    self.style.MIGRATE_HEADING("Synchronizing apps without migrations:")
                )
            if options["app_label"]:
                self.sync_apps(connection, [app_label])
            else:
                self.sync_apps(connection, executor.loader.unmigrated_apps)

        # Migrate!
        if self.verbosity >= 1:
            self.stdout.write(self.style.MIGRATE_HEADING("Running migrations:"))
        if not plan:
            if self.verbosity >= 1:
                self.stdout.write("  No migrations to apply.")
                # If there's changes that aren't in migrations yet, tell them
                # how to fix it.
                autodetector = MigrationAutodetector(
                    executor.loader.project_state(),
                    ProjectState.from_apps(apps),
                )
                changes = autodetector.changes(graph=executor.loader.graph)
                if changes:
                    self.stdout.write(
                        self.style.NOTICE(
                            "  Your models in app(s): %s have changes that are not "
                            "yet reflected in a migration, and so won't be "
                            "applied." % ", ".join(repr(app) for app in sorted(changes))
                        )
                    )
                    self.stdout.write(
                        self.style.NOTICE(
                            "  Run 'manage.py makemigrations' to make new "
                            "migrations, and then re-run 'manage.py migrate' to "
                            "apply them."
                        )
                    )
            fake = False
            fake_initial = False
        else:
            fake = options["fake"]
            fake_initial = options["fake_initial"]
        # Note: Here we apply migration
        post_migrate_state = executor.migrate(
            targets,
            plan=plan,
            state=pre_migrate_state.clone(),
            fake=fake,
            fake_initial=fake_initial,
        )
        from itertools import chain
        from bluegreen.fields import AddFieldPatched
        
        operations = []
        for migration, _ in plan:
            operations.extend(migration.operations)

        if any(isinstance(op, AddFieldPatched) for op in operations):
            # Wrap data migration in transaction for safety
            with transaction.atomic():
                for migration, _ in plan:
                    for operation in migration.operations:
                        if isinstance(operation, AddFieldPatched):
                            table_name = migration.app_label + '_' + operation.model_name
                            with connection.cursor() as cursor:
                                # SQL injection protection: use quote_name for identifiers
                                cursor.execute(
                                    f"UPDATE {connection.ops.quote_name(table_name)} "
                                    f"SET {connection.ops.quote_name(operation.name)} = "
                                    f"{connection.ops.quote_name(operation.old_name)}"
                                )

        # post_migrate signals have access to all models. Ensure that all models
        # are reloaded in case any are delayed.
        post_migrate_state.clear_delayed_apps_cache()
        post_migrate_apps = post_migrate_state.apps

        # Re-render models of real apps to include relationships now that
        # we've got a final state. This wouldn't be necessary if real apps
        # models were rendered with relationships in the first place.
        with post_migrate_apps.bulk_update():
            model_keys = []
            for model_state in post_migrate_apps.real_models:
                model_key = model_state.app_label, model_state.name_lower
                model_keys.append(model_key)
                post_migrate_apps.unregister_model(*model_key)
        post_migrate_apps.render_multiple(
            [ModelState.from_model(apps.get_model(*model)) for model in model_keys]
        )

        # Send the post_migrate signal, so individual apps can do whatever they need
        # to do at this point.
        emit_post_migrate_signal(
            self.verbosity,
            self.interactive,
            connection.alias,
            stdout=self.stdout,
            apps=post_migrate_apps,
            plan=plan,
        )