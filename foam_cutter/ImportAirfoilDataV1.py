"""Script to import Lednicer or Selig airfoil sections into Rhino
Points will be interpolated with degree 3 curves/choice of knot style
Sections may be one (Selig) or two (Lednicer) curves, Lednicer will be joined
Previously used settings are remembered within same session.
File format info from here: http://airfoiltools.com/airfoiltools/airfoil/index

Script by Mitch Heynick 05.11.15. Version 1.0, lightly tested.

To change "default" knotstyle, in #get previous settings below:
Change 'else: prev_style=' from 0(Uniform) to 1(Chord) or 2(SqrtChord)
To change the "default" to not add points, change 'else: prev_pts' to False"""

import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino

def VerifyHeaderString(line_str):
    if line_str.strip()=="": return
    split_line=line_str.split()
    if len(split_line)==2:
        try:
            A=float(split_line[0])
            B=float(split_line[1])
            if A and B: return
        except: pass
    return True
    
def TryGetTwoIntegers(line_str):
    if line_str.strip()=="": return
    split_line=line_str.split()
    try:
        A=int(float(split_line[0].strip()))
        B=int(float(split_line[1].strip()))
        if A and B: return A,B
    except: return
        
def TryGetTwoFloats(line_str):
    if line_str.strip()=="": return
    split_line=line_str.split()
    try:
        x_c=float(split_line[0])
        y_c=float(split_line[1])
        if (x_c != None and y_c != None) and (x_c<1.1 and y_c<1.1):
            #line is a good data point
            return x_c, y_c
    except: return
    
def ParseFileBody(line_list,start,end,limit):
    pt_list=[] ; count=0
    for i in range(start,limit):
        xy=TryGetTwoFloats(line_list[i])
        if xy:
            pt_list.append(Rhino.Geometry.Point3d(xy[0],xy[1],0))
            count+=1
            if count==end: break
    return i+1,pt_list
    
def AddScaledCrv(pt_list,k_style,sf,name):
    s_pts=rs.PointArrayTransform(pt_list,rs.XformScale(sf))
    crv=rs.AddInterpCurve(s_pts,3,k_style)
    rs.ObjectName(crv,name)
    return crv,s_pts
    
def CommandLineOptions(msg,ini,limits):
    go = Rhino.Input.Custom.GetNumber()
    go.SetCommandPrompt(msg[0])
    
    lstOption1 = go.AddOptionList(msg[1],limits[1],ini[1])
    blnOption2 = Rhino.Input.Custom.OptionToggle(ini[2],limits[2][0],limits[2][1])
    
    go.AddOptionToggle(msg[2],blnOption2)
    go.SetDefaultNumber(ini[0])
    go.SetLowerLimit(limits[0],True)
    
    go.AcceptNothing(True)
    index=ini[2]
    while True:
        get_rc = go.Get()
        b=blnOption2.CurrentValue
        if go.CommandResult()== Rhino.Commands.Result.Cancel: return
        elif go.CommandResult()== Rhino.Commands.Result.Nothing: break
        elif get_rc==Rhino.Input.GetResult.Number: break
        elif get_rc==Rhino.Input.GetResult.Option:
            if go.OptionIndex()==lstOption1:
                index = go.Option().CurrentListOptionIndex
            continue
        break
    return (go.Number(),b,index)
    
def ImportAirfoilData():
    #prompt for file
    filename = rs.OpenFileName("Open", "Airfoil Data File (*.dat)|*.dat||")
    if not filename: return
    file=open(filename, 'r')
    if not file: return
    
    #get previous settings
    if "ImpAirfoilScale" in sc.sticky: prev_scale = sc.sticky["ImpAirfoilScale"]
    else: prev_scale = 1.0
    if "ImpAirfoilStyle" in sc.sticky: prev_style = sc.sticky["ImpAirfoilStyle"]
    else: prev_style = 0
    if "ImpAirfoilPts" in sc.sticky: prev_pts = sc.sticky["ImpAirfoilPts"]
    else: prev_pts = True
    
    #get command line options
    tol=rs.UnitAbsoluteTolerance()
    msg=["Scale along X axis?","KnotStyle","AddPoints",]
    ini=[prev_scale,prev_style,prev_pts]
    params=[tol,["Uniform","Chord","SqrtChord"],["No","Yes"]]
    options=CommandLineOptions(msg,ini,params)
    if not options: return
    
    #read all the file into a list line by line
    lines=file.readlines()
    if not lines:
        err_msg="Unable to read file!"
        rs.MessageBox(err_msg,48) ; return
        
    #check header line
    if not VerifyHeaderString(lines[0]):
        err_msg="File has no header info!"
        rs.MessageBox(err_msg,48) ; return
    else: obj_name=lines[0]
    
    #parse rest of file
    rs.EnableRedraw(False)
    err_msg="Unable to create profile from file data"
    result=TryGetTwoIntegers(lines[1])
    if result:
        #Lednicer file format (upper/lower profiles, lead edge point duplicated)
        upc,lpc=result
        #upper profile
        next_line,pts=ParseFileBody(lines,2,upc,len(lines))
        if len(pts)>3:
            UcrvID,scaled_pts=AddScaledCrv(pts,options[2],options[0],obj_name)
            if options[1]: rs.AddPoints(scaled_pts)
        else:
            rs.MessageBox(err_msg,48) ; return
        #lower profile
        next_line,pts=ParseFileBody(lines,next_line,lpc,len(lines))
        if len(pts)>3:
            LcrvID,scaled_pts=AddScaledCrv(pts,options[2],options[0],obj_name)
            if options[1]:
                #remove first point to avoid duplicates
                scaled_pts.pop(0)
                rs.AddPoints(scaled_pts)
        else:
            rs.MessageBox(err_msg,48) ; return
        #join upper and lower profiles
        if UcrvID and LcrvID:
            crvID=rs.JoinCurves([UcrvID,LcrvID],True)
    else:
        #Selig file format
        next_line,pts=ParseFileBody(lines,1,len(lines),len(lines))
        if len(pts)>3:
            crvID,scaled_pts=AddScaledCrv(pts,options[2],options[0],obj_name)
            if options[1]:
                #remove last point to avoid duplicates
                scaled_pts.pop()
                rs.AddPoints(scaled_pts)
        else:
            rs.MessageBox(err_msg,48) ; return
            
    file.close()
    #set preferences
    sc.sticky["ImpAirfoilScale"] = options[0]
    sc.sticky["ImpAirfoilStyle"] = options[2]
    sc.sticky["ImpAirfoilPts"] = options[1]
    
ImportAirfoilData()