# -*- coding: utf-8 -*-
#@+leo-ver=5-thin
#@+node:ekr.20150514041209.1: * @file ../commands/editFileCommands.py
#@@first
'''Leo's file-editing commands.'''
#@+<< imports >>
#@+node:ekr.20150514050328.1: ** << imports >> (editFileCommands.py)
import difflib
import os
import leo.core.leoGlobals as g
from leo.commands.baseCommands import BaseEditCommandsClass as BaseEditCommandsClass
#@-<< imports >>

def cmd(name):
    '''Command decorator for the EditFileCommandsClass class.'''
    return g.new_cmd_decorator(name, ['c', 'editFileCommands',])

class EditFileCommandsClass(BaseEditCommandsClass):
    '''A class to load files into buffers and save buffers to files.'''
    #@+others
    #@+node:ekr.20150514063305.356: ** efc.compareAnyTwoFiles & helpers
    @cmd('file-compare-leo-files')
    def compareAnyTwoFiles(self, event):
        '''Compare two files.'''
        trace = False and not g.unitTesting
        c = c1 = self.c
        w = c.frame.body.wrapper
        commanders = g.app.commanders()
        if g.app.diff:
            if len(commanders) == 2:
                c1, c2 = commanders
                fn1 = g.shortFileName(c1.wrappedFileName) or c1.shortFileName()
                fn2 = g.shortFileName(c2.wrappedFileName) or c2.shortFileName()
                g.es('--diff auto compare', color='red')
                g.es(fn1)
                g.es(fn2)
            else:
                g.es('expecting two .leo files')
                return
        else:
            # Prompt for the file to be compared with the present outline.
            filetypes = [("Leo files", "*.leo"), ("All files", "*"),]
            fileName = g.app.gui.runOpenFileDialog(c,
                title="Compare .leo Files", filetypes=filetypes, defaultextension='.leo')
            if not fileName: return
            # Read the file into the hidden commander.
            c2 = self.createHiddenCommander(fileName)
            if not c2: return
        # Compute the inserted, deleted and changed dicts.
        d1 = self.createFileDict(c1)
        d2 = self.createFileDict(c2)
        inserted, deleted, changed = self.computeChangeDicts(d1, d2)
        if trace: self.dumpCompareNodes(fileName, c1.mFileName, inserted, deleted, changed)
        # Create clones of all inserted, deleted and changed dicts.
        self.createAllCompareClones(c1, c2, inserted, deleted, changed)
        # Fix bug 1231656: File-Compare-Leo-Files leaves other file open-count incremented.
        if not g.app.diff:
            g.app.forgetOpenFile(fn=c2.fileName(), force=True)
            c2.frame.destroySelf()
            g.app.gui.set_focus(c, w)
    #@+node:ekr.20150514063305.357: *3* efc.computeChangeDicts
    def computeChangeDicts(self, d1, d2):
        '''
        Compute inserted, deleted, changed dictionaries.

        New in Leo 4.11: show the nodes in the *invisible* file, d2, if possible.
        '''
        inserted = {}
        for key in d2:
            if not d1.get(key):
                inserted[key] = d2.get(key)
        deleted = {}
        for key in d1:
            if not d2.get(key):
                deleted[key] = d1.get(key)
        changed = {}
        for key in d1:
            if d2.get(key):
                p1 = d1.get(key)
                p2 = d2.get(key)
                if p1.h != p2.h or p1.b != p2.b:
                    changed[key] = p2 # Show the node in the *other* file.
        return inserted, deleted, changed
    #@+node:ekr.20150514063305.358: *3* efc.createAllCompareClones & helper
    def createAllCompareClones(self, c1, c2, inserted, deleted, changed):
        '''Create the comparison trees.'''
        c = self.c # Always use the visible commander
        assert c == c1
        # Create parent node at the start of the outline.
        u, undoType = c.undoer, 'Compare Two Files'
        u.beforeChangeGroup(c.p, undoType)
        undoData = u.beforeInsertNode(c.p)
        parent = c.p.insertAfter()
        parent.setHeadString(undoType)
        u.afterInsertNode(parent, undoType, undoData, dirtyVnodeList=[])
        # Use the wrapped file name if possible.
        fn1 = g.shortFileName(c1.wrappedFileName) or c1.shortFileName()
        fn2 = g.shortFileName(c2.wrappedFileName) or c2.shortFileName()
        for d, kind in (
            (deleted, 'not in %s' % fn2),
            (inserted, 'not in %s' % fn1),
            (changed, 'changed: as in %s' % fn2),
        ):
            self.createCompareClones(d, kind, parent)
        c.selectPosition(parent)
        u.afterChangeGroup(parent, undoType, reportFlag=True)
        c.redraw()
    #@+node:ekr.20150514063305.359: *4* efc.createCompareClones
    def createCompareClones(self, d, kind, parent):
        if d:
            c = self.c # Use the visible commander.
            parent = parent.insertAsLastChild()
            parent.setHeadString(kind)
            for key in d:
                p = d.get(key)
                if not kind.endswith('.leo') and p.isAnyAtFileNode():
                    # Don't make clones of @<file> nodes for wrapped files.
                    pass
                elif p.v.context == c:
                    clone = p.clone()
                    clone.moveToLastChildOf(parent)
                else:
                    # Fix bug 1160660: File-Compare-Leo-Files creates "other file" clones.
                    copy = p.copyTreeAfter()
                    copy.moveToLastChildOf(parent)
                    for p2 in copy.self_and_subtree():
                        p2.v.context = c
    #@+node:ekr.20150514063305.360: *3* efc.createHiddenCommander
    def createHiddenCommander(self, fn):
        '''Read the file into a hidden commander (Similar to g.openWithFileName).'''
        import leo.core.leoCommands as leoCommands
        lm = g.app.loadManager
        c2 = leoCommands.Commands(fn, gui=g.app.nullGui)
        theFile = lm.openLeoOrZipFile(fn)
        if theFile:
            c2.fileCommands.openLeoFile(theFile, fn, readAtFileNodesFlag=True, silent=True)
            return c2
        else:
            return None
    #@+node:ekr.20150514063305.361: *3* efc.createFileDict
    def createFileDict(self, c):
        '''Create a dictionary of all relevant positions in commander c.'''
        d = {}
        for p in c.all_positions():
            d[p.v.fileIndex] = p.copy()
        return d
    #@+node:ekr.20150514063305.362: *3* efc.dumpCompareNodes
    def dumpCompareNodes(self, fileName1, fileName2, inserted, deleted, changed):
        for d, kind in (
            (inserted, 'inserted (only in %s)' % (fileName1)),
            (deleted, 'deleted  (only in %s)' % (fileName2)),
            (changed, 'changed'),
        ):
            g.pr('\n', kind)
            for key in d:
                p = d.get(key)
                if g.isPython3:
                    g.pr('%-32s %s' % (key, p.h))
                else:
                    g.pr('%-32s %s' % (key, g.toEncodedString(p.h, 'ascii')))
    #@+node:ekr.20150722080425.1: ** efc.compareTrees
    def compareTrees(self, p1, p2, tag):
        
        class Controller:
            #@+others
            #@+node:ekr.20150722080308.2: *3* ct.compare
            def compare(self, d1, d2, p1, p2, root):
                '''Compare dicts d1 and d2.'''
                c = self.c
                for h in sorted(d1.keys()):
                    p1, p2 = d1.get(h), d2.get(h)
                    if h in d2:
                        lines1, lines2 = g.splitLines(p1.b), g.splitLines(p2.b)
                        aList = list(difflib.unified_diff(lines1, lines2, 'vr1', 'vr2'))
                        if aList:
                            p = root.insertAsLastChild()
                            p.h = h
                            p.b = ''.join(aList)
                            p1.clone().moveToLastChildOf(p)
                            p2.clone().moveToLastChildOf(p)
                    elif p1.b.strip():
                        # Only in p1 tree, and not an organizer node.
                        p = root.insertAsLastChild()
                        p.h = h + '(%s only)' % p1.h
                        p1.clone().moveToLastChildOf(p)
                for h in sorted(d2.keys()):
                    p2 = d2.get(h)
                    if h not in d1 and p2.b.strip():
                        # Only in p2 tree, and not an organizer node.
                        p = root.insertAsLastChild()
                        p.h = h + '(%s only)' % p2.h
                        p2.clone().moveToLastChildOf(p)
                return root
            #@+node:ekr.20150722080308.3: *3* ct.run
            def run(self, c, p1, p2, tag):
                '''Main line.'''
                self.c = c
                root = c.p.insertAfter()
                root.h = tag
                d1 = self.scan(p1)
                d2 = self.scan(p2)
                self.compare(d1, d2, p1, p2, root)
                c.p.contract()
                root.expand()
                c.selectPosition(root)
                c.redraw()
            #@+node:ekr.20150722080308.4: *3* ct.scan
            def scan(self, p1):
                '''
                Create a dict of the methods in p1.
                Keys are headlines, stripped of prefixes.
                Values are copies of positions.
                '''
                d = {} # 
                for p in p1.self_and_subtree():
                    h = p.h.strip()
                    i = h.find('.')
                    if i > -1:
                        h = h[i + 1:].strip()
                    if h in d:
                        g.es_print('duplicate', p.h)
                    else:
                        d[h] = p.copy()
                return d
            #@-others
            
        Controller().run(self.c, p1, p2, tag)
    #@+node:ekr.20150514063305.363: ** efc.deleteFile
    @cmd('file-delete')
    def deleteFile(self, event):
        '''Prompt for the name of a file and delete it.'''
        k = self.c.k
        state = k.getState('delete_file')
        if state == 0:
            k.setLabelBlue('Delete File: ')
            k.extendLabel(os.getcwd() + os.sep)
            k.getArg(event, 'delete_file', 1, self.deleteFile)
        else:
            k.keyboardQuit()
            k.clearState()
            try:
                os.remove(k.arg)
                k.setStatusLabel('Deleted: %s' % k.arg)
            except Exception:
                k.setStatusLabel('Not Deleted: %s' % k.arg)
    #@+node:ekr.20150514063305.364: ** efc.diff
    @cmd('file-diff-files')
    def diff(self, event=None):
        '''Creates a node and puts the diff between 2 files into it.'''
        c = self.c
        fn = self.getReadableTextFile()
        if not fn: return
        fn2 = self.getReadableTextFile()
        if not fn2: return
        s1, e = g.readFileIntoString(fn)
        if s1 is None: return
        s2, e = g.readFileIntoString(fn2)
        if s2 is None: return
        lines1, lines2 = g.splitLines(s1), g.splitLines(s2)
        aList = difflib.ndiff(lines1, lines2)
        p = c.p.insertAfter()
        p.h = 'diff'
        p.b = ''.join(aList)
        c.redraw()
    #@+node:ekr.20150514063305.365: ** efc.getReadableTextFile
    def getReadableTextFile(self):
        '''Prompt for a text file.'''
        c = self.c
        fn = g.app.gui.runOpenFileDialog(c,
            title='Open Text File',
            filetypes=[("Text", "*.txt"), ("All files", "*")],
            defaultextension=".txt")
        return fn
    #@+node:ekr.20150514063305.366: ** efc.insertFile
    @cmd('file-insert')
    def insertFile(self, event):
        '''Prompt for the name of a file and put the selected text into it.'''
        w = self.editWidget(event)
        if not w:
            return
        fn = self.getReadableTextFile()
        if not fn:
            return
        s, e = g.readFileIntoString(fn)
        if s:
            self.beginCommand(w, undoType='insert-file')
            i = w.getInsertPoint()
            w.insert(i, s)
            w.seeInsertPoint()
            self.endCommand(changed=True, setLabel=True)
    #@+node:ekr.20160111190632.1: ** efc.makeStubFiles
    @cmd('make-stub-files')
    def make_stub_files(self, event):
        #@+<< make-stub-files-docstring >>
        #@+node:ekr.20160127040557.2: *3* << make-stub-files-docstring >>
        #@@language rest
        #@@nowrap

        '''
        This command eliminates much of the drudgery of creating python stub (.pyi)
        files https://www.python.org/dev/peps/pep-0484/#stub-files from python
        source files. It writes stub files for all @<file> nodes in the selected
        outline. The @string stub-output-directory setting tells where to write
        files. By default, this is the ~/stubs directory.

        Overview
        ========

        Leo settings specify:
        - **naming conventions** telling the types of arguments and other variables.
        - Various **patterns** to be applied to return values.
        - A list of **prefix lines** to be inserted verbatim at the start of each stub file.

        This command never creates directories automatically, nor does it overwrite
        stub files unless the @bool stub-overwrite setting is in effect.

        For each source file, the script does the following:

        1. The script writes the prefix lines verbatim. This makes it easy to add
           common code to the start of stub files. For example::

            from typing import TypeVar, Iterable, Tuple
            T = TypeVar('T', int, float, complex)
            
        2. The script walks the parse (ast) tree for the source file, generating
           stub lines for each function, class or method. The script generates no
           stub lines for defs nested within other defs. Return values are handled
           in a clever way as described below.

        For example, given the naming conventions::

            aList: Sequence
            i: int
            c: Commander
            s: str
            
        and a function::

            def scan(s, i, x):
                whatever
                
        the script will generate::

            def scan(s: str, i:int, x): --> (return values: see next section):
            
        Handling function returns
        =========================
            
        The script handles function returns pragmatically. The tree walker simply
        writes a list of return expressions for each def. For example, here is the
        *default* output at the start of leoAst.pyi, before any patterns are applied::

            class AstDumper:
                def dump(self, node: ast.Ast, level=number) -> 
                    repr(node), 
                    str%(name,sep,sep1.join(aList)), 
                    str%(name,str.join(aList)), 
                    str%str.join(str%(sep,self.dump(z,level+number)) for z in node): ...
                def get_fields(self, node: ast.Ast) -> result: ...
                def extra_attributes(self, node: ast.Ast) -> Sequence: ...
                
        The stub for the dump function is not syntactically correct because there
        are four returns listed.

        The configuration file can specify several kinds of patterns to be applied
        to return values. Just a few patterns (given below) will convert::

            def dump(self, node: ast.Ast, level=number) -> 
                repr(node), 
                str%(name,sep,sep1.join(aList)), 
                str%(name,str.join(aList)), 
                str%str.join(str%(sep,self.dump(z,level+number)) for z in node): ...
                
        to:

            def dump(self, node: ast.Ast, level=number) -> str: ... 

        If multiple return values still remain after applying all patterns, you
        must edit stubs to specify a proper return type. And even if only a single
        value remains, its "proper" value may not obvious from naming conventions.
        In that case, you will have to update the stub using the actual source code
        as a guide.

        Settings
        ========

        ``@string stub-output-directory = ~/stubs``

        The location of the output directory

        ``@data stub-arg-types``
           
        Lines to be inserted at the start of each stub file.

        ``@data stub-arg-types``
                
        Specifies naming conventions. These conventions are applied to *both*
        argument lists *and* return values.
          
        - For argument lists, the replacement becomes the annotation.
        - For return values, the replacement *replaces* the pattern.

        For example::
            
            aList: Sequence
            aList2: Sequence
            c: Commander
            i: int
            j: int
            k: int
            node: ast.Ast
            p: Position
            s: str
            s2: str
            v: VNode
            
        ``@data stub-def-name-patterns``
            
        Specifies the *final* return value to be associated with functions or
        methods. The pattern is a regex matching the names of defs. Methods names
        should have the form class_name.method_name. No further pattern matching is
        done if any of these patterns match. For example::
            
            AstFormatter.do_.*: str
            StubTraverser.format_returns: str
            StubTraverser.indent: str
            
        ``@data stub-return-balanced-patterns``

        Specifies **balanced patterns** to be applied to return values. Balanced
        patterns match verbatim, except that the patterns ``(*), [*], and {*}``
        match only *balanced* parens, square and curly brackets.

        Return values are rescanned until no more balanced patterns apply. Balanced
        patterns are *much* simpler to use than regex's. Indeed, the following
        balanced patterns suffice to collapse most string expressions to str::

            repr(*): str
            str.join(*): str
            str.replace(*): str
            str%(*): str
            str%str: str

        ``@data stub-return-regex-patterns``
            
        Specifies regex patterns to be applied to return values. These patterns are
        applied last, after all other patterns have been applied. Again, these
        regex patterns are applied repeatedly until no further replacements are
        possible. For example::

            .*__name__: str
            
        **Note**: Return patterns are applied to each individual return value
        separately. Comments never appear in return values, and all strings in
        return values appear as str. As a result, there is no context to worry
        about and very short patterns suffice.
        '''
        #@-<< make-stub-files-docstring >>
        #@+others
        #@+node:ekr.20160111202214.1: *3* class MakeStubFile
        class MakeStubFile:
            '''A class to make Python stub (.pyi) files.'''
            #@+<< MakeStubFile change log >>
            #@+node:ekr.20160127043809.1: *4* << MakeStubFile change log >>
            #@+at
            #@@language rest
            #@@wrap
            # 
            # Changes made to bring this code nearer to StandAloneMakeStubFile class.
            # 
            # - changed self.d to self.args.d.
            # 
            # - Added show_data() to dump all data.
            # 
            # - Added finalize() from the stand-alone class.
            # 
            # - Added scan() method and changed scan_d method:
            #     - scan_d now splits lines on ":", not blank.
            #     - This allows the same patterns to be used as with the stand-alone version.
            #@-<< MakeStubFile change log >>
            #@+others
            #@+node:ekr.20160112104836.1: *4* msf.ctors & helpers
            def __init__(self, c):
                self.c = c
                # From @data nodes...
                self.args_d = self.scan_d('stub-arg-types')
                self.def_pattern_d = self.scan_d('stub-def-name-patterns')
                self.prefix_lines = self.scan('stub-prefix-lines')
                self.return_pattern_d = self.scan_d('stub-return-balanced-patterns')
                self.return_regex_d = self.scan_d('stub-return-regex-patterns')
                # State ivars...
                self.output_directory = self.finalize(
                    c.config.getString('stub-output-directory') or '~/stubs')
                self.overwrite = c.config.getBool('stub-overwrite', default=False)
            #@+node:ekr.20160127045807.1: *5* msf.scan
            def scan(self, kind):
                '''Return a list of *all* lines from an @data node, including comments.'''
                c = self.c
                aList = c.config.getData(kind,
                    strip_comments=False,
                    strip_data=False)
                if not aList:
                    g.trace('warning: no @data %s node' % kind)
                return aList
            #@+node:ekr.20160112104450.1: *5* msf.scan_d
            def scan_d(self, kind):
                '''Return a dict created from an @data node of the given kind.'''
                trace = False and not g.unitTesting
                c = self.c
                aList = c.config.getData(kind,
                    strip_comments=True,
                    strip_data=True)
                d = {}
                if not aList:
                    g.trace('warning: no @data %s node' % kind)
                for s in aList:
                    name, value = s.split(':',1)
                    # g.trace('name',name,'value',value)
                    d[name.strip()] = value.strip()
                if trace:
                    print('@data %s...' % kind)
                    for key in sorted(d.keys()):
                        print('  %s: %s' % (key, d.get(key)))
                return d
            #@+node:ekr.20160127043632.1: *4* msf.finalize
            def finalize(self, fn):
                '''Finalize and regularize a filename.'''
                return g.os_path_normpath(g.os_path_abspath(g.os_path_expanduser(fn)))
            #@+node:ekr.20160111202214.4: *4* msf.make_stub_file
            def make_stub_file(self, p):
                '''Make a stub file in ~/stubs for the @<file> node at p.'''
                import ast
                import leo.core.leoAst as leoAst
                assert p.isAnyAtFileNode()
                c = self.c
                fn = p.anyAtFileNodeName()
                if not fn.endswith('.py'):
                    g.es_print('not a python file', fn)
                    return
                abs_fn = g.fullPath(c, p)
                if not g.os_path_exists(abs_fn):
                    g.es_print('not found', abs_fn)
                    return
                ### stubs = self.finalize('~/stubs/output')
                if g.os_path_exists(self.output_directory):
                    base_fn = g.os_path_basename(fn)
                    out_fn = g.os_path_finalize_join(self.output_directory, base_fn)
                else:
                    g.es_print('not found', self.output_directory)
                    return
                out_fn = out_fn[:-3] + '.pyi'
                out_fn = os.path.normpath(out_fn)
                s = open(abs_fn).read()
                node = ast.parse(s,filename=fn,mode='exec')
                leoAst.StubTraverser(controller=self, ).run(node, out_fn)
            #@+node:ekr.20160111202214.3: *4* msf.run
            def run(self, p):
                '''Make stub files for all files in p's tree.'''
                if p.isAnyAtFileNode():
                    self.make_stub_file(p)
                    return
                # First, look down tree.
                after, p2 = p.nodeAfterTree(), p.firstChild()
                found = False
                while p2 and p != after:
                    if p2.isAnyAtFileNode():
                        self.make_stub_file(p2)
                        p2.moveToNext()
                        found = True
                    else:
                        p2.moveToThreadNext()
                if not found:
                    # Look up the tree.
                    for p2 in p.parents():
                        if p2.isAnyAtFileNode():
                            self.make_stub_file(p2)
                            break
                    else:
                        g.es('no files found in tree:', p.h)
            #@-others
        #@-others
        MakeStubFile(self.c).run(self.c.p)
    #@+node:ekr.20150514063305.367: ** efc.makeDirectory
    @cmd('directory-make')
    def makeDirectory(self, event):
        '''Prompt for the name of a directory and create it.'''
        k = self.c.k
        state = k.getState('make_directory')
        if state == 0:
            k.setLabelBlue('Make Directory: ')
            k.extendLabel(os.getcwd() + os.sep)
            k.getArg(event, 'make_directory', 1, self.makeDirectory)
        else:
            k.keyboardQuit()
            k.clearState()
            try:
                os.mkdir(k.arg)
                k.setStatusLabel("Created: %s" % k.arg)
            except Exception:
                k.setStatusLabel("Not Create: %s" % k.arg)
    #@+node:ekr.20150514063305.368: ** efc.openOutlineByName
    @cmd('file-open-by-name')
    def openOutlineByName(self, event):
        '''file-open-by-name: Prompt for the name of a Leo outline and open it.'''
        c, k = self.c, self.c.k
        fileName = ''.join(k.givenArgs)
        # Bug fix: 2012/04/09: only call g.openWithFileName if the file exists.
        if fileName and g.os_path_exists(fileName):
            g.openWithFileName(fileName, old_c=c)
        else:
            k.setLabelBlue('Open Leo Outline: ')
            k.getFileName(event, callback=self.openOutlineByNameFinisher)

    def openOutlineByNameFinisher(self, fn):
        c = self.c
        if fn and g.os_path_exists(fn) and not g.os_path_isdir(fn):
            c2 = g.openWithFileName(fn, old_c=c)
            try:
                g.app.gui.runAtIdle(c2.treeWantsFocusNow)
            except Exception:
                pass
        else:
            g.es('ignoring: %s' % fn)
    #@+node:ekr.20150514063305.369: ** efc.removeDirectory
    @cmd('directory-remove')
    def removeDirectory(self, event):
        '''Prompt for the name of a directory and delete it.'''
        k = self.c.k
        state = k.getState('remove_directory')
        if state == 0:
            k.setLabelBlue('Remove Directory: ')
            k.extendLabel(os.getcwd() + os.sep)
            k.getArg(event, 'remove_directory', 1, self.removeDirectory)
        else:
            k.keyboardQuit()
            k.clearState()
            try:
                os.rmdir(k.arg)
                k.setStatusLabel('Removed: %s' % k.arg)
            except Exception:
                k.setStatusLabel('Not Removed: %s' % k.arg)
    #@+node:ekr.20150514063305.370: ** efc.saveFile
    @cmd('file-save')
    def saveFile(self, event):
        '''Prompt for the name of a file and put the body text of the selected node into it..'''
        c = self.c
        w = self.editWidget(event)
        if not w:
            return
        fileName = g.app.gui.runSaveFileDialog(c,
            initialfile=None,
            title='save-file',
            filetypes=[("Text", "*.txt"), ("All files", "*")],
            defaultextension=".txt")
        if fileName:
            try:
                f = open(fileName, 'w')
                s = w.getAllText()
                if not g.isPython3: # 2010/08/27
                    s = g.toEncodedString(s, encoding='utf-8', reportErrors=True)
                f.write(s)
                f.close()
            except IOError:
                g.es('can not create', fileName)
    #@-others
#@-leo
