import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';
import { 
  Search, Plus, Edit, Trash2, Calendar, FileText, Pill, Users, Home, LogOut, Eye, EyeOff, 
  Clock, Calculator, Scan, AlertTriangle, Package, DollarSign, ChevronDown, ChevronUp,
  Activity, TrendingUp, BarChart3, CalendarDays
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Utility functions
const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString('es-ES');
};

const formatDateTime = (dateTimeString) => {
  return new Date(dateTimeString).toLocaleString('es-ES');
};

const formatCurrency = (amount) => {
  return new Intl.NumberFormat('es-HN', {
    style: 'currency',
    currency: 'HNL',
    minimumFractionDigits: 2
  }).format(amount);
};

const calcularEdad = (fechaNacimiento) => {
  const today = new Date();
  const birthDate = new Date(fechaNacimiento);
  let age = today.getFullYear() - birthDate.getFullYear();
  const m = today.getMonth() - birthDate.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
    age--;
  }
  return age;
};

// Login Component
const Login = ({ onLogin }) => {
  const [codigo, setCodigo] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await axios.post(`${API}/login`, { codigo });
      if (response.data.success) {
        localStorage.setItem('token', response.data.token);
        localStorage.setItem('role', response.data.role);
        onLogin(response.data.token, response.data.role);
      }
    } catch (error) {
      alert('Código de acceso incorrecto');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-indigo-600 rounded-full flex items-center justify-center">
            <Users className="h-8 w-8 text-white" />
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            Sistema de Clínica Pediátrica
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Ingrese su código de acceso
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleLogin}>
          <div>
            <label htmlFor="codigo" className="sr-only">
              Código de acceso
            </label>
            <div className="relative">
              <input
                id="codigo"
                name="codigo"
                type={showPassword ? "text" : "password"}
                required
                value={codigo}
                onChange={(e) => setCodigo(e.target.value)}
                className="appearance-none rounded-lg relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Código de acceso"
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5 text-gray-400" />
                ) : (
                  <Eye className="h-5 w-5 text-gray-400" />
                )}
              </button>
            </div>
          </div>
          
          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Ingresando...' : 'Ingresar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Dashboard Component
const Dashboard = ({ token, role, onLogout }) => {
  const [activeView, setActiveView] = useState('patients');
  const [pacientes, setPacientes] = useState([]);
  const [medicamentos, setMedicamentos] = useState([]);
  const [codigosCIE10, setCodigosCIE10] = useState([]);
  const [citas, setCitas] = useState([]);
  const [loading, setLoading] = useState(false);

  // Headers for authenticated requests
  const headers = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json'
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [pacientesRes, medicamentosRes, cie10Res, citasRes] = await Promise.all([
        axios.get(`${API}/pacientes`, { headers }),
        axios.get(`${API}/medicamentos`, { headers }),
        axios.get(`${API}/cie10`, { headers }),
        axios.get(`${API}/citas/semana`, { headers })
      ]);
      
      setPacientes(pacientesRes.data);
      setMedicamentos(medicamentosRes.data);
      setCodigosCIE10(cie10Res.data);
      setCitas(citasRes.data);
    } catch (error) {
      console.error('Error loading initial data:', error);
    }
    setLoading(false);
  };

  const MenuItem = ({ icon: Icon, label, view, active, onClick }) => (
    <button
      onClick={() => onClick(view)}
      className={`w-full flex items-center px-4 py-3 text-left hover:bg-indigo-50 transition-colors ${
        active ? 'bg-indigo-100 text-indigo-700 border-r-2 border-indigo-500' : 'text-gray-700'
      }`}
    >
      <Icon className="h-5 w-5 mr-3" />
      {label}
    </button>
  );

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className="w-64 bg-white shadow-lg">
        <div className="p-4 bg-indigo-600 text-white">
          <h1 className="text-lg font-semibold">Clínica Pediátrica</h1>
          <p className="text-sm text-indigo-200">Dr. {role}</p>
        </div>
        
        <nav className="mt-4">
          <MenuItem
            icon={Home}
            label="Dashboard"
            view="dashboard"
            active={activeView === 'dashboard'}
            onClick={setActiveView}
          />
          <MenuItem
            icon={Users}
            label="Pacientes"
            view="patients"
            active={activeView === 'patients'}
            onClick={setActiveView}
          />
          <MenuItem
            icon={CalendarDays}
            label="Calendario de Citas"
            view="appointments"
            active={activeView === 'appointments'}
            onClick={setActiveView}
          />
          <MenuItem
            icon={Pill}
            label="Farmacia"
            view="pharmacy"
            active={activeView === 'pharmacy'}
            onClick={setActiveView}
          />
          <MenuItem
            icon={FileText}
            label="Códigos CIE-10"
            view="cie10"
            active={activeView === 'cie10'}
            onClick={setActiveView}
          />
        </nav>
        
        <div className="absolute bottom-4 left-4 right-4">
          <button
            onClick={onLogout}
            className="w-full flex items-center px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <LogOut className="h-5 w-5 mr-3" />
            Cerrar Sesión
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {activeView === 'dashboard' && <DashboardView pacientes={pacientes} medicamentos={medicamentos} citas={citas} />}
        {activeView === 'patients' && (
          <PatientsView 
            pacientes={pacientes} 
            setPacientes={setPacientes}
            codigosCIE10={codigosCIE10}
            headers={headers}
          />
        )}
        {activeView === 'appointments' && (
          <AppointmentsView 
            citas={citas} 
            setCitas={setCitas}
            pacientes={pacientes}
            headers={headers}
          />
        )}
        {activeView === 'pharmacy' && (
          <PharmacyView 
            medicamentos={medicamentos} 
            setMedicamentos={setMedicamentos}
            headers={headers}
          />
        )}
        {activeView === 'cie10' && <CIE10View codigosCIE10={codigosCIE10} />}
      </div>
    </div>
  );
};

// Dashboard View Component
const DashboardView = ({ pacientes, medicamentos, citas }) => {
  const totalPacientes = pacientes.length;
  const pacientesEsteAno = pacientes.filter(p => 
    new Date(p.created_at).getFullYear() === new Date().getFullYear()
  ).length;
  
  const medicamentosBajoStock = medicamentos.filter(m => m.stock <= m.stock_minimo).length;
  const citasHoy = citas.filter(c => 
    new Date(c.fecha_hora).toDateString() === new Date().toDateString()
  ).length;
  
  const pacientesRecientes = pacientes
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 5);

  const citasProximas = citas
    .filter(c => new Date(c.fecha_hora) >= new Date())
    .sort((a, b) => new Date(a.fecha_hora) - new Date(b.fecha_hora))
    .slice(0, 5);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition-shadow">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Users className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Pacientes</p>
              <p className="text-2xl font-bold text-gray-900">{totalPacientes}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition-shadow">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <CalendarDays className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Citas Hoy</p>
              <p className="text-2xl font-bold text-gray-900">{citasHoy}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition-shadow">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <TrendingUp className="h-8 w-8 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Pacientes Este Año</p>
              <p className="text-2xl font-bold text-gray-900">{pacientesEsteAno}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition-shadow">
          <div className="flex items-center">
            <div className="p-2 bg-red-100 rounded-lg">
              <AlertTriangle className="h-8 w-8 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Medicamentos Bajo Stock</p>
              <p className="text-2xl font-bold text-gray-900">{medicamentosBajoStock}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Two column layout for tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Patients */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Pacientes Recientes</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Paciente
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Estado
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {pacientesRecientes.map((paciente) => (
                  <tr key={paciente.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{paciente.nombre_completo}</div>
                      <div className="text-sm text-gray-500">{paciente.edad} años</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        paciente.estado_nutricional === 'normal' ? 'bg-green-100 text-green-800' :
                        paciente.estado_nutricional === 'desnutrido' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {paciente.estado_nutricional || 'No evaluado'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Upcoming Appointments */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Próximas Citas</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Paciente
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Fecha/Hora
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {citasProximas.map((cita) => (
                  <tr key={cita.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{cita.paciente_nombre}</div>
                      <div className="text-sm text-gray-500">{cita.motivo}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{formatDateTime(cita.fecha_hora)}</div>
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        cita.estado === 'confirmada' ? 'bg-green-100 text-green-800' :
                        cita.estado === 'pendiente' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {cita.estado}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

// Patients View Component
const PatientsView = ({ pacientes, setPacientes, codigosCIE10, headers }) => {
  const [showModal, setShowModal] = useState(false);
  const [editingPatient, setEditingPatient] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPatient, setSelectedPatient] = useState(null);

  const filteredPacientes = pacientes.filter(p => 
    p.nombre_completo.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.numero_celular.includes(searchTerm)
  );

  const openPatientModal = (patient = null) => {
    setEditingPatient(patient);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingPatient(null);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Gestión de Pacientes</h1>
        <button
          onClick={() => openPatientModal()}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg flex items-center"
        >
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Paciente
        </button>
      </div>

      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar paciente por nombre o teléfono..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Patients List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredPacientes.map((paciente) => (
          <PatientCard
            key={paciente.id}
            paciente={paciente}
            onEdit={() => openPatientModal(paciente)}
            onView={() => setSelectedPatient(paciente)}
            headers={headers}
            setPacientes={setPacientes}
          />
        ))}
      </div>

      {/* Modals */}
      {showModal && (
        <PatientModal
          patient={editingPatient}
          codigosCIE10={codigosCIE10}
          onClose={closeModal}
          headers={headers}
          setPacientes={setPacientes}
        />
      )}

      {selectedPatient && (
        <PatientDetailModal
          patient={selectedPatient}
          onClose={() => setSelectedPatient(null)}
          headers={headers}
        />
      )}
    </div>
  );
};

// Patient Card Component
const PatientCard = ({ paciente, onEdit, onView, headers, setPacientes }) => {
  const handleDelete = async () => {
    if (window.confirm('¿Está seguro de eliminar este paciente?')) {
      try {
        await axios.delete(`${API}/pacientes/${paciente.id}`, { headers });
        setPacientes(prev => prev.filter(p => p.id !== paciente.id));
      } catch (error) {
        alert('Error al eliminar paciente');
      }
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{paciente.nombre_completo}</h3>
        <div className="flex space-x-2">
          <button
            onClick={onView}
            className="p-1 text-blue-600 hover:bg-blue-50 rounded"
          >
            <Eye className="h-4 w-4" />
          </button>
          <button
            onClick={onEdit}
            className="p-1 text-gray-600 hover:bg-gray-50 rounded"
          >
            <Edit className="h-4 w-4" />
          </button>
          <button
            onClick={handleDelete}
            className="p-1 text-red-600 hover:bg-red-50 rounded"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
      
      <div className="space-y-2 text-sm text-gray-600">
        <p><span className="font-medium">Edad:</span> {paciente.edad} años</p>
        <p><span className="font-medium">Teléfono:</span> {paciente.numero_celular}</p>
        <p><span className="font-medium">Padres:</span> {paciente.nombre_padre} / {paciente.nombre_madre}</p>
        {paciente.diagnostico_clinico && (
          <p><span className="font-medium">Diagnóstico:</span> {paciente.diagnostico_clinico}</p>
        )}
        {paciente.capitulo_cie10 && (
          <p className="text-xs"><span className="font-medium">CIE-10:</span> {paciente.codigo_cie10}</p>
        )}
        {paciente.estado_nutricional && (
          <div className="flex items-center">
            <span className="font-medium">Estado Nutricional:</span>
            <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
              paciente.estado_nutricional === 'normal' ? 'bg-green-100 text-green-800' :
              paciente.estado_nutricional === 'desnutrido' ? 'bg-red-100 text-red-800' :
              'bg-yellow-100 text-yellow-800'
            }`}>
              {paciente.estado_nutricional}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

// Patient Modal Component (Create/Edit) - ENHANCED
const PatientModal = ({ patient, codigosCIE10, onClose, headers, setPacientes }) => {
  const [formData, setFormData] = useState({
    nombre_completo: patient?.nombre_completo || '',
    fecha_nacimiento: patient?.fecha_nacimiento || '',
    nombre_padre: patient?.nombre_padre || '',
    nombre_madre: patient?.nombre_madre || '',
    direccion: patient?.direccion || '',
    numero_celular: patient?.numero_celular || '',
    sintomas_signos: patient?.sintomas_signos || '',
    diagnostico_clinico: patient?.diagnostico_clinico || '',
    tratamiento_medico: patient?.tratamiento_medico || '', // NUEVO CAMPO
    codigo_cie10: patient?.codigo_cie10 || '',
    gravedad_diagnostico: patient?.gravedad_diagnostico || '',
    peso: patient?.peso || '',
    altura: patient?.altura || '',
    contacto_recordatorios: patient?.contacto_recordatorios || ''
  });

  const [filteredCIE10, setFilteredCIE10] = useState([]);
  const [showCIE10List, setShowCIE10List] = useState(false);
  const [cieAutoSuggestion, setCieAutoSuggestion] = useState(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({...prev, [name]: value}));

    // Auto-clasificación CIE-10 cuando se escribe el diagnóstico
    if (name === 'diagnostico_clinico' && value.length > 3) {
      classifyDiagnosis(value);
    }

    // Filter CIE-10 codes when typing
    if (name === 'codigo_cie10' && value.length > 0) {
      const filtered = codigosCIE10.filter(code =>
        code.codigo.toLowerCase().includes(value.toLowerCase()) ||
        code.descripcion.toLowerCase().includes(value.toLowerCase())
      );
      setFilteredCIE10(filtered.slice(0, 10));
      setShowCIE10List(true);
    } else if (name === 'codigo_cie10') {
      setShowCIE10List(false);
    }
  };

  // NUEVA FUNCIÓN: Clasificación automática CIE-10
  const classifyDiagnosis = async (diagnostico) => {
    try {
      const response = await axios.post(`${API}/cie10/clasificar?diagnostico=${encodeURIComponent(diagnostico)}`, {}, { headers });
      if (response.data.sugerencia) {
        setCieAutoSuggestion(response.data);
      }
    } catch (error) {
      console.error('Error en clasificación automática:', error);
    }
  };

  const selectCIE10Code = (code) => {
    setFormData(prev => ({...prev, codigo_cie10: code.codigo}));
    setShowCIE10List(false);
    setCieAutoSuggestion(null);
  };

  const acceptAutoSuggestion = () => {
    if (cieAutoSuggestion) {
      setFormData(prev => ({...prev, codigo_cie10: cieAutoSuggestion.codigo}));
      setCieAutoSuggestion(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const dataToSubmit = {
        ...formData,
        fecha_nacimiento: formData.fecha_nacimiento,
        peso: formData.peso ? parseFloat(formData.peso) : null,
        altura: formData.altura ? parseFloat(formData.altura) : null
      };

      let response;
      if (patient) {
        response = await axios.put(`${API}/pacientes/${patient.id}`, dataToSubmit, { headers });
        setPacientes(prev => prev.map(p => p.id === patient.id ? response.data : p));
      } else {
        response = await axios.post(`${API}/pacientes`, dataToSubmit, { headers });
        setPacientes(prev => [...prev, response.data]);
      }
      
      onClose();
    } catch (error) {
      alert('Error al guardar paciente: ' + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-screen overflow-y-auto">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">
            {patient ? 'Editar Paciente' : 'Nuevo Paciente'}
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Información Personal */}
            <div className="border-l-4 border-blue-500 pl-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Información Personal</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nombre Completo *
                  </label>
                  <input
                    type="text"
                    name="nombre_completo"
                    required
                    value={formData.nombre_completo}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Fecha de Nacimiento *
                  </label>
                  <input
                    type="date"
                    name="fecha_nacimiento"
                    required
                    value={formData.fecha_nacimiento}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Número de Celular *
                  </label>
                  <input
                    type="tel"
                    name="numero_celular"
                    required
                    value={formData.numero_celular}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nombre del Padre *
                  </label>
                  <input
                    type="text"
                    name="nombre_padre"
                    required
                    value={formData.nombre_padre}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nombre de la Madre *
                  </label>
                  <input
                    type="text"
                    name="nombre_madre"
                    required
                    value={formData.nombre_madre}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>
              
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Dirección *
                </label>
                <textarea
                  name="direccion"
                  required
                  value={formData.direccion}
                  onChange={handleInputChange}
                  rows="2"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            {/* Información Médica */}
            <div className="border-l-4 border-green-500 pl-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Información Médica</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Peso (kg)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    name="peso"
                    value={formData.peso}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Altura (m)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    name="altura"
                    value={formData.altura}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Síntomas y Signos Clínicos
                  </label>
                  <textarea
                    name="sintomas_signos"
                    value={formData.sintomas_signos}
                    onChange={handleInputChange}
                    rows="3"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Describa los síntomas observados..."
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Diagnóstico Clínico
                  </label>
                  <textarea
                    name="diagnostico_clinico"
                    value={formData.diagnostico_clinico}
                    onChange={handleInputChange}
                    rows="2"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Escriba el diagnóstico para clasificación automática CIE-10..."
                  />
                  
                  {/* Auto-sugerencia CIE-10 */}
                  {cieAutoSuggestion && (
                    <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded-md">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-green-800">
                            Clasificación CIE-10 sugerida: {cieAutoSuggestion.codigo}
                          </p>
                          <p className="text-sm text-green-700">{cieAutoSuggestion.descripcion}</p>
                          <p className="text-xs text-green-600">{cieAutoSuggestion.capitulo}</p>
                        </div>
                        <button
                          type="button"
                          onClick={acceptAutoSuggestion}
                          className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                        >
                          Aceptar
                        </button>
                      </div>
                    </div>
                  )}
                </div>
                
                {/* NUEVO CAMPO: Tratamiento Médico */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tratamiento Médico
                  </label>
                  <textarea
                    name="tratamiento_medico"
                    value={formData.tratamiento_medico}
                    onChange={handleInputChange}
                    rows="3"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Describa el tratamiento prescrito..."
                  />
                </div>
              </div>
            </div>

            {/* Clasificación CIE-10 */}
            <div className="border-l-4 border-purple-500 pl-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Clasificación CIE-10</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="relative">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Código CIE-10
                  </label>
                  <input
                    type="text"
                    name="codigo_cie10"
                    value={formData.codigo_cie10}
                    onChange={handleInputChange}
                    placeholder="Escriba para buscar código CIE-10..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  
                  {showCIE10List && filteredCIE10.length > 0 && (
                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                      {filteredCIE10.map((code) => (
                        <button
                          key={code.id}
                          type="button"
                          onClick={() => selectCIE10Code(code)}
                          className="w-full text-left px-3 py-2 hover:bg-gray-100 border-b border-gray-100"
                        >
                          <div className="font-medium text-sm">{code.codigo}</div>
                          <div className="text-xs text-gray-600">{code.descripcion}</div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Gravedad del Diagnóstico
                  </label>
                  <select
                    name="gravedad_diagnostico"
                    value={formData.gravedad_diagnostico}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Seleccionar gravedad</option>
                    <option value="leve">Leve</option>
                    <option value="moderada">Moderada</option>
                    <option value="grave">Grave</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Información Adicional */}
            <div className="border-l-4 border-yellow-500 pl-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Información Adicional</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Contacto para Recordatorios
                </label>
                <input
                  type="text"
                  name="contacto_recordatorios"
                  value={formData.contacto_recordatorios}
                  onChange={handleInputChange}
                  placeholder="Teléfono o email para recordatorios de citas"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
            
            <div className="flex justify-end space-x-3 mt-6">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                {patient ? 'Actualizar' : 'Crear'} Paciente
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// Patient Detail Modal Component
const PatientDetailModal = ({ patient, onClose, headers }) => {
  const [showAddCita, setShowAddCita] = useState(false);
  const [showAddAnalisis, setShowAddAnalisis] = useState(false);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-screen overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">{patient.nombre_completo}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
          
          {/* Patient Basic Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-3">Información Personal</h3>
              <div className="space-y-2 text-sm">
                <p><span className="font-medium">Edad:</span> {patient.edad} años</p>
                <p><span className="font-medium">Fecha de Nacimiento:</span> {formatDate(patient.fecha_nacimiento)}</p>
                <p><span className="font-medium">Padre:</span> {patient.nombre_padre}</p>
                <p><span className="font-medium">Madre:</span> {patient.nombre_madre}</p>
                <p><span className="font-medium">Teléfono:</span> {patient.numero_celular}</p>
                <p><span className="font-medium">Dirección:</span> {patient.direccion}</p>
                {patient.contacto_recordatorios && (
                  <p><span className="font-medium">Contacto Recordatorios:</span> {patient.contacto_recordatorios}</p>
                )}
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-3">Estado Nutricional</h3>
              <div className="space-y-2 text-sm">
                {patient.peso && <p><span className="font-medium">Peso:</span> {patient.peso} kg</p>}
                {patient.altura && <p><span className="font-medium">Altura:</span> {patient.altura} m</p>}
                {patient.imc && <p><span className="font-medium">IMC:</span> {patient.imc}</p>}
                {patient.estado_nutricional && (
                  <p>
                    <span className="font-medium">Estado:</span> 
                    <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
                      patient.estado_nutricional === 'normal' ? 'bg-green-100 text-green-800' :
                      patient.estado_nutricional === 'desnutrido' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {patient.estado_nutricional}
                    </span>
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Clinical Info */}
          {(patient.sintomas_signos || patient.diagnostico_clinico || patient.tratamiento_medico || patient.codigo_cie10) && (
            <div className="mb-6">
              <h3 className="font-semibold text-gray-900 mb-3">Información Clínica</h3>
              <div className="bg-gray-50 p-4 rounded-lg space-y-3">
                {patient.sintomas_signos && (
                  <div>
                    <span className="font-medium text-sm">Síntomas y Signos:</span>
                    <p className="text-sm text-gray-700 mt-1">{patient.sintomas_signos}</p>
                  </div>
                )}
                {patient.diagnostico_clinico && (
                  <div>
                    <span className="font-medium text-sm">Diagnóstico Clínico:</span>
                    <p className="text-sm text-gray-700 mt-1">{patient.diagnostico_clinico}</p>
                  </div>
                )}
                {patient.tratamiento_medico && (
                  <div>
                    <span className="font-medium text-sm">Tratamiento Médico:</span>
                    <p className="text-sm text-gray-700 mt-1">{patient.tratamiento_medico}</p>
                  </div>
                )}
                {patient.codigo_cie10 && (
                  <div>
                    <span className="font-medium text-sm">Código CIE-10:</span>
                    <p className="text-sm text-gray-700 mt-1">
                      {patient.codigo_cie10} - {patient.descripcion_cie10}
                    </p>
                    {patient.capitulo_cie10 && (
                      <p className="text-xs text-gray-600 mt-1">{patient.capitulo_cie10}</p>
                    )}
                  </div>
                )}
                {patient.gravedad_diagnostico && (
                  <div>
                    <span className="font-medium text-sm">Gravedad:</span>
                    <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
                      patient.gravedad_diagnostico === 'leve' ? 'bg-green-100 text-green-800' :
                      patient.gravedad_diagnostico === 'moderada' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {patient.gravedad_diagnostico}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Medical History Tabs would go here */}
          <div className="space-y-4">
            <div className="flex space-x-4">
              <button
                onClick={() => setShowAddCita(true)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm"
              >
                <Plus className="h-4 w-4 inline mr-1" />
                Agregar Cita
              </button>
              <button
                onClick={() => setShowAddAnalisis(true)}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm"
              >
                <Plus className="h-4 w-4 inline mr-1" />
                Agregar Análisis
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// NEW: Appointments View Component
const AppointmentsView = ({ citas, setCitas, pacientes, headers }) => {
  const [showModal, setShowModal] = useState(false);
  const [selectedWeek, setSelectedWeek] = useState(getCurrentWeek());
  const [viewMode, setViewMode] = useState('week'); // week, day

  function getCurrentWeek() {
    const today = new Date();
    const startOfWeek = new Date(today);
    startOfWeek.setDate(today.getDate() - today.getDay());
    return startOfWeek;
  }

  const weekDays = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
  
  const getWeekDates = () => {
    const dates = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(selectedWeek);
      date.setDate(selectedWeek.getDate() + i);
      dates.push(date);
    }
    return dates;
  };

  const getCitasForDate = (date) => {
    return citas.filter(cita => {
      const citaDate = new Date(cita.fecha_hora);
      return citaDate.toDateString() === date.toDateString();
    }).sort((a, b) => new Date(a.fecha_hora) - new Date(b.fecha_hora));
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Calendario de Citas</h1>
        <div className="flex space-x-4">
          <button
            onClick={() => setShowModal(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg flex items-center"
          >
            <Plus className="h-4 w-4 mr-2" />
            Nueva Cita
          </button>
        </div>
      </div>

      {/* Week Navigation */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => {
              const newWeek = new Date(selectedWeek);
              newWeek.setDate(selectedWeek.getDate() - 7);
              setSelectedWeek(newWeek);
            }}
            className="px-3 py-2 text-gray-600 hover:bg-gray-100 rounded"
          >
            ← Semana Anterior
          </button>
          <h2 className="text-lg font-semibold">
            {selectedWeek.toLocaleDateString('es-ES')} - {
              new Date(selectedWeek.getTime() + 6 * 24 * 60 * 60 * 1000).toLocaleDateString('es-ES')
            }
          </h2>
          <button
            onClick={() => {
              const newWeek = new Date(selectedWeek);
              newWeek.setDate(selectedWeek.getDate() + 7);
              setSelectedWeek(newWeek);
            }}
            className="px-3 py-2 text-gray-600 hover:bg-gray-100 rounded"
          >
            Siguiente Semana →
          </button>
        </div>
        
        <button
          onClick={() => setSelectedWeek(getCurrentWeek())}
          className="px-3 py-2 bg-indigo-100 text-indigo-700 rounded"
        >
          Hoy
        </button>
      </div>

      {/* Weekly Calendar Grid */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="grid grid-cols-7 gap-0">
          {/* Day Headers */}
          {weekDays.map((day, index) => (
            <div key={day} className="bg-gray-50 p-4 text-center font-semibold border-r border-gray-200">
              <div className="text-sm text-gray-600">{day}</div>
              <div className="text-lg">{getWeekDates()[index].getDate()}</div>
            </div>
          ))}
          
          {/* Day Cells */}
          {getWeekDates().map((date, index) => (
            <div key={index} className="min-h-32 p-2 border-r border-t border-gray-200">
              <div className="space-y-1">
                {getCitasForDate(date).map((cita) => (
                  <div 
                    key={cita.id}
                    className={`p-2 rounded text-xs ${
                      cita.estado === 'confirmada' ? 'bg-green-100 text-green-800' :
                      cita.estado === 'pendiente' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}
                  >
                    <div className="font-semibold">
                      {new Date(cita.fecha_hora).toLocaleTimeString('es-ES', {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </div>
                    <div className="truncate">{cita.paciente_nombre}</div>
                    <div className="truncate text-gray-600">{cita.motivo}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* New Appointment Modal */}
      {showModal && (
        <AppointmentModal
          onClose={() => setShowModal(false)}
          pacientes={pacientes}
          headers={headers}
          setCitas={setCitas}
        />
      )}
    </div>
  );
};

// NEW: Appointment Modal Component
const AppointmentModal = ({ onClose, pacientes, headers, setCitas }) => {
  const [formData, setFormData] = useState({
    paciente_id: '',
    fecha_hora: '',
    motivo: '',
    doctor: 'Dr. Usuario',
    notas: ''
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({...prev, [name]: value}));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const dataToSubmit = {
        ...formData,
        fecha_hora: new Date(formData.fecha_hora).toISOString()
      };

      const response = await axios.post(`${API}/citas`, dataToSubmit, { headers });
      setCitas(prev => [...prev, response.data]);
      onClose();
    } catch (error) {
      alert('Error al crear cita: ' + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-md w-full">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">Nueva Cita Médica</h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Paciente *
              </label>
              <select
                name="paciente_id"
                required
                value={formData.paciente_id}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Seleccionar paciente</option>
                {pacientes.map(paciente => (
                  <option key={paciente.id} value={paciente.id}>
                    {paciente.nombre_completo} - {paciente.edad} años
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fecha y Hora *
              </label>
              <input
                type="datetime-local"
                name="fecha_hora"
                required
                value={formData.fecha_hora}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Motivo de la Cita *
              </label>
              <input
                type="text"
                name="motivo"
                required
                value={formData.motivo}
                onChange={handleInputChange}
                placeholder="Ej: Consulta general, seguimiento, vacunación"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Doctor
              </label>
              <input
                type="text"
                name="doctor"
                value={formData.doctor}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Notas
              </label>
              <textarea
                name="notas"
                value={formData.notas}
                onChange={handleInputChange}
                rows="2"
                placeholder="Notas adicionales sobre la cita"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div className="flex justify-end space-x-3 mt-6">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                Crear Cita
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// ENHANCED: Pharmacy View Component with Complex Pricing
const PharmacyView = ({ medicamentos, setMedicamentos, headers }) => {
  const [showModal, setShowModal] = useState(false);
  const [showCalculator, setShowCalculator] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const categorias = [
    'all',
    'Antibióticos',
    'Analgésicos', 
    'Antiinflamatorios',
    'Vitaminas',
    'Jarabe para la tos',
    'Antialérgicos',
    'Probióticos',
    'Cremas y ungüentos',
    'Cosméticos', // Nueva categoría
    'Otros'
  ];

  const filteredMedicamentos = medicamentos.filter(m => {
    const matchesSearch = m.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         m.categoria.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         m.codigo_barras.includes(searchTerm);
    const matchesCategory = selectedCategory === 'all' || m.categoria === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const medicamentosBajoStock = medicamentos.filter(m => m.stock <= m.stock_minimo);
  const medicamentosVencer = medicamentos.filter(m => {
    if (!m.fecha_vencimiento) return false;
    const diasRestantes = Math.ceil((new Date(m.fecha_vencimiento) - new Date()) / (1000 * 60 * 60 * 24));
    return diasRestantes <= 30 && diasRestantes > 0;
  });

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Gestión de Farmacia</h1>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowCalculator(true)}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center"
          >
            <Calculator className="h-4 w-4 mr-2" />
            Calculadora de Precios
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg flex items-center"
          >
            <Plus className="h-4 w-4 mr-2" />
            Nuevo Medicamento
          </button>
        </div>
      </div>

      {/* Alert Cards */}
      {(medicamentosBajoStock.length > 0 || medicamentosVencer.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {medicamentosBajoStock.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center">
                <AlertTriangle className="h-5 w-5 text-red-600 mr-2" />
                <h3 className="text-sm font-medium text-red-800">Stock Bajo</h3>
              </div>
              <p className="text-sm text-red-700 mt-1">
                {medicamentosBajoStock.length} medicamento(s) con stock por debajo del mínimo
              </p>
            </div>
          )}
          
          {medicamentosVencer.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-center">
                <Clock className="h-5 w-5 text-yellow-600 mr-2" />
                <h3 className="text-sm font-medium text-yellow-800">Próximos a Vencer</h3>
              </div>
              <p className="text-sm text-yellow-700 mt-1">
                {medicamentosVencer.length} medicamento(s) vencen en los próximos 30 días
              </p>
            </div>
          )}
        </div>
      )}

      {/* Search and Filters */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="md:col-span-2 relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por nombre, categoría o código de barras..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        >
          {categorias.map(cat => (
            <option key={cat} value={cat}>
              {cat === 'all' ? 'Todas las categorías' : cat}
            </option>
          ))}
        </select>
      </div>

      {/* Medications Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredMedicamentos.map((medicamento) => (
          <MedicationCard
            key={medicamento.id}
            medicamento={medicamento}
            headers={headers}
            setMedicamentos={setMedicamentos}
          />
        ))}
      </div>

      {/* Modals */}
      {showModal && (
        <MedicationModal
          onClose={() => setShowModal(false)}
          headers={headers}
          setMedicamentos={setMedicamentos}
        />
      )}

      {showCalculator && (
        <PriceCalculatorModal
          onClose={() => setShowCalculator(false)}
        />
      )}
    </div>
  );
};

// ENHANCED: Medication Card Component
const MedicationCard = ({ medicamento, headers, setMedicamentos }) => {
  const [showDetails, setShowDetails] = useState(false);
  
  const isLowStock = medicamento.stock <= medicamento.stock_minimo;
  const isNearExpiry = medicamento.fecha_vencimiento && 
    Math.ceil((new Date(medicamento.fecha_vencimiento) - new Date()) / (1000 * 60 * 60 * 24)) <= 30;

  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow">
      <div className="p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{medicamento.nombre}</h3>
            <p className="text-sm text-gray-600">{medicamento.categoria}</p>
          </div>
          
          <div className="flex space-x-1">
            {isLowStock && (
              <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full">
                Stock Bajo
              </span>
            )}
            {isNearExpiry && (
              <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                Por Vencer
              </span>
            )}
          </div>
        </div>
        
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Stock:</span>
            <span className={`font-medium ${isLowStock ? 'text-red-600' : 'text-gray-900'}`}>
              {medicamento.stock} unidades
            </span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-600">Precio Público:</span>
            <span className="font-medium text-green-600">{formatCurrency(medicamento.precio_publico)}</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-600">Margen:</span>
            <span className="font-medium text-blue-600">{medicamento.margen_utilidad}%</span>
          </div>
          
          {medicamento.codigo_barras && (
            <div className="flex justify-between">
              <span className="text-gray-600">Código Barras:</span>
              <span className="font-mono text-xs">{medicamento.codigo_barras}</span>
            </div>
          )}
          
          {medicamento.fecha_vencimiento && (
            <div className="flex justify-between">
              <span className="text-gray-600">Vencimiento:</span>
              <span className={`text-xs ${isNearExpiry ? 'text-yellow-600' : 'text-gray-600'}`}>
                {formatDate(medicamento.fecha_vencimiento)}
              </span>
            </div>
          )}
          
          {medicamento.dosis_pediatrica && (
            <div>
              <span className="text-gray-600">Dosis Pediátrica:</span>
              <p className="text-xs text-gray-700 mt-1">{medicamento.dosis_pediatrica}</p>
            </div>
          )}
        </div>
        
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="mt-4 w-full flex items-center justify-center px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg"
        >
          {showDetails ? 'Ocultar Detalles' : 'Ver Detalles'}
          {showDetails ? <ChevronUp className="ml-1 h-4 w-4" /> : <ChevronDown className="ml-1 h-4 w-4" />}
        </button>
        
        {showDetails && (
          <div className="mt-4 pt-4 border-t border-gray-200 space-y-2 text-sm">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="text-gray-600">Costo Base:</span>
                <p className="text-xs">{formatCurrency(medicamento.costo_base)}</p>
              </div>
              <div>
                <span className="text-gray-600">Precio Base:</span>
                <p className="text-xs">{formatCurrency(medicamento.precio_base)}</p>
              </div>
              <div>
                <span className="text-gray-600">Escala:</span>
                <p className="text-xs">{medicamento.escala_compra}</p>
              </div>
              <div>
                <span className="text-gray-600">Descuento:</span>
                <p className="text-xs">{medicamento.descuento_aplicable}%</p>
              </div>
            </div>
            
            {medicamento.lote && (
              <div>
                <span className="text-gray-600">Lote:</span>
                <span className="ml-2 text-xs">{medicamento.lote}</span>
              </div>
            )}
            
            {medicamento.proveedor && (
              <div>
                <span className="text-gray-600">Proveedor:</span>
                <span className="ml-2 text-xs">{medicamento.proveedor}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// NEW: Price Calculator Modal Component
const PriceCalculatorModal = ({ onClose }) => {
  const [formData, setFormData] = useState({
    costo_base: '',
    escala_compra: 'sin_escala',
    descuento: '0',
    impuesto: '15'
  });
  
  const [resultado, setResultado] = useState(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({...prev, [name]: value}));
  };

  const calcularPrecios = async () => {
    try {
      const params = new URLSearchParams({
        costo_base: formData.costo_base,
        escala_compra: formData.escala_compra,
        descuento: formData.descuento,
        impuesto: formData.impuesto
      });
      
      const response = await axios.post(`${API}/medicamentos/calcular-precios?${params}`, {}, {
        headers: { Authorization: `Bearer valid_token_1970` }
      });
      
      setResultado(response.data);
    } catch (error) {
      alert('Error al calcular precios: ' + error.message);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">Calculadora de Precios con Margen 25%</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Input Section */}
            <div className="space-y-4">
              <h3 className="font-semibold text-gray-900">Datos de Entrada</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Costo Base (L) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  name="costo_base"
                  required
                  value={formData.costo_base}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Ej: 100.00"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Escala de Compra
                </label>
                <select
                  name="escala_compra"
                  value={formData.escala_compra}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="sin_escala">Sin escala</option>
                  <option value="10+3">10+3 (Compra 10, recibe 13)</option>
                  <option value="6+2">6+2 (Compra 6, recibe 8)</option>
                  <option value="5+1">5+1 (Compra 5, recibe 6)</option>
                  <option value="3+1">3+1 (Compra 3, recibe 4)</option>
                  <option value="1+1">1+1 (Compra 1, recibe 2)</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descuento Aplicable (%)
                </label>
                <input
                  type="number"
                  step="0.1"
                  name="descuento"
                  value={formData.descuento}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Ej: 5"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Impuesto (%)
                </label>
                <input
                  type="number"
                  step="0.1"
                  name="impuesto"
                  value={formData.impuesto}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Ej: 15"
                />
              </div>
              
              <button
                onClick={calcularPrecios}
                disabled={!formData.costo_base}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg disabled:opacity-50"
              >
                <Calculator className="h-4 w-4 inline mr-2" />
                Calcular Precios
              </button>
            </div>
            
            {/* Results Section */}
            <div className="space-y-4">
              <h3 className="font-semibold text-gray-900">Resultados</h3>
              
              {resultado ? (
                <div className="bg-green-50 p-4 rounded-lg space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-700">Costo Real:</span>
                    <span className="font-semibold">{formatCurrency(resultado.costo_real)}</span>
                  </div>
                  
                  <div className="flex justify-between">
                    <span className="text-gray-700">Precio Base (sin descuento):</span>
                    <span className="font-semibold">{formatCurrency(resultado.precio_base)}</span>
                  </div>
                  
                  <div className="flex justify-between">
                    <span className="text-gray-700">Precio Público (con descuento):</span>
                    <span className="font-semibold text-green-600">{formatCurrency(resultado.precio_publico)}</span>
                  </div>
                  
                  <div className="flex justify-between">
                    <span className="text-gray-700">Precio Final (después descuento):</span>
                    <span className="font-semibold">{formatCurrency(resultado.precio_final)}</span>
                  </div>
                  
                  <div className="flex justify-between text-lg">
                    <span className="text-gray-900 font-semibold">Margen de Utilidad:</span>
                    <span className="font-bold text-green-600">{resultado.margen_utilidad}%</span>
                  </div>
                  
                  {resultado.margen_utilidad >= 25 && (
                    <div className="bg-green-100 border border-green-400 text-green-700 px-3 py-2 rounded text-sm">
                      ✓ Margen cumple con el mínimo del 25%
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-gray-50 p-4 rounded-lg text-center text-gray-500">
                  Ingrese los datos y presione "Calcular Precios" para ver los resultados
                </div>
              )}
            </div>
          </div>
          
          <div className="flex justify-end mt-6">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ENHANCED: Medication Modal Component
const MedicationModal = ({ onClose, headers, setMedicamentos }) => {
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    codigo_barras: '',
    stock: '',
    stock_minimo: '5',
    costo_base: '',
    escala_compra: 'sin_escala',
    descuento_aplicable: '0',
    impuesto: '15',
    categoria: '',
    lote: '',
    fecha_vencimiento: '',
    proveedor: '',
    indicaciones: '',
    contraindicaciones: '',
    dosis_pediatrica: ''
  });

  const [previewPrecios, setPreviewPrecios] = useState(null);

  const categorias = [
    'Antibióticos',
    'Analgésicos', 
    'Antiinflamatorios',
    'Vitaminas',
    'Jarabe para la tos',
    'Antialérgicos',
    'Probióticos',
    'Cremas y ungüentos',
    'Cosméticos', // Nueva categoría
    'Otros'
  ];

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({...prev, [name]: value}));
    
    // Auto-calculate prices when cost parameters change
    if (['costo_base', 'escala_compra', 'descuento_aplicable', 'impuesto'].includes(name)) {
      calculatePricesPreview({...formData, [name]: value});
    }
  };

  const calculatePricesPreview = async (data) => {
    if (!data.costo_base) return;
    
    try {
      const params = new URLSearchParams({
        costo_base: data.costo_base,
        escala_compra: data.escala_compra,
        descuento: data.descuento_aplicable,
        impuesto: data.impuesto
      });
      
      const response = await axios.post(`${API}/medicamentos/calcular-precios?${params}`, {}, { headers });
      setPreviewPrecios(response.data);
    } catch (error) {
      console.error('Error calculating preview prices:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const dataToSubmit = {
        ...formData,
        stock: parseInt(formData.stock),
        stock_minimo: parseInt(formData.stock_minimo),
        costo_base: parseFloat(formData.costo_base),
        descuento_aplicable: parseFloat(formData.descuento_aplicable),
        impuesto: parseFloat(formData.impuesto),
        fecha_vencimiento: formData.fecha_vencimiento || null
      };

      const response = await axios.post(`${API}/medicamentos`, dataToSubmit, { headers });
      setMedicamentos(prev => [...prev, response.data]);
      onClose();
    } catch (error) {
      alert('Error al crear medicamento: ' + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-screen overflow-y-auto">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">Nuevo Medicamento</h2>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Información Básica */}
            <div className="border-l-4 border-blue-500 pl-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Información Básica</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nombre del Medicamento *
                  </label>
                  <input
                    type="text"
                    name="nombre"
                    required
                    value={formData.nombre}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Categoría *
                  </label>
                  <select
                    name="categoria"
                    required
                    value={formData.categoria}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Seleccionar categoría</option>
                    {categorias.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Código de Barras
                  </label>
                  <input
                    type="text"
                    name="codigo_barras"
                    value={formData.codigo_barras}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* Inventario */}
            <div className="border-l-4 border-green-500 pl-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Control de Inventario</h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Stock Inicial *
                  </label>
                  <input
                    type="number"
                    name="stock"
                    required
                    min="0"
                    value={formData.stock}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Stock Mínimo
                  </label>
                  <input
                    type="number"
                    name="stock_minimo"
                    min="0"
                    value={formData.stock_minimo}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Lote
                  </label>
                  <input
                    type="text"
                    name="lote"
                    value={formData.lote}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Fecha de Vencimiento
                  </label>
                  <input
                    type="date"
                    name="fecha_vencimiento"
                    value={formData.fecha_vencimiento}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* Precios y Costos */}
            <div className="border-l-4 border-yellow-500 pl-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Cálculo de Precios (Margen 25%)</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Costo Base (L) *
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      name="costo_base"
                      required
                      min="0"
                      value={formData.costo_base}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Escala de Compra
                    </label>
                    <select
                      name="escala_compra"
                      value={formData.escala_compra}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="sin_escala">Sin escala</option>
                      <option value="10+3">10+3</option>
                      <option value="6+2">6+2</option>
                      <option value="5+1">5+1</option>
                      <option value="3+1">3+1</option>
                      <option value="1+1">1+1</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Descuento Aplicable (%)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      name="descuento_aplicable"
                      min="0"
                      max="50"
                      value={formData.descuento_aplicable}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Impuesto (%)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      name="impuesto"
                      min="0"
                      value={formData.impuesto}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>
                
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-3">Vista Previa de Precios</h4>
                  {previewPrecios ? (
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>Costo Real:</span>
                        <span>{formatCurrency(previewPrecios.costo_real)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Precio Base:</span>
                        <span>{formatCurrency(previewPrecios.precio_base)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="font-medium">Precio Público:</span>
                        <span className="font-medium text-green-600">{formatCurrency(previewPrecios.precio_publico)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="font-medium">Margen:</span>
                        <span className="font-medium text-blue-600">{previewPrecios.margen_utilidad}%</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">Ingrese el costo base para ver la vista previa</p>
                  )}
                </div>
              </div>
            </div>

            {/* Información Médica */}
            <div className="border-l-4 border-purple-500 pl-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Información Médica</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Descripción *
                  </label>
                  <textarea
                    name="descripcion"
                    required
                    value={formData.descripcion}
                    onChange={handleInputChange}
                    rows="2"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Dosis Pediátrica
                  </label>
                  <textarea
                    name="dosis_pediatrica"
                    value={formData.dosis_pediatrica}
                    onChange={handleInputChange}
                    rows="2"
                    placeholder="Ej: 5ml cada 8 horas por 7 días"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Indicaciones
                    </label>
                    <textarea
                      name="indicaciones"
                      value={formData.indicaciones}
                      onChange={handleInputChange}
                      rows="2"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Contraindicaciones
                    </label>
                    <textarea
                      name="contraindicaciones"
                      value={formData.contraindicaciones}
                      onChange={handleInputChange}
                      rows="2"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Proveedor */}
            <div className="border-l-4 border-indigo-500 pl-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Información del Proveedor</h3>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Proveedor
                </label>
                <input
                  type="text"
                  name="proveedor"
                  value={formData.proveedor}
                  onChange={handleInputChange}
                  placeholder="Nombre del proveedor o distribuidor"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
            
            <div className="flex justify-end space-x-3 mt-6">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                Crear Medicamento
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// CIE-10 View Component (Enhanced with Chapters)
const CIE10View = ({ codigosCIE10 }) => {
  const [searchTerm, setSearchTerm] = useState('');
  
  const filteredCodes = codigosCIE10.filter(code =>
    code.codigo.toLowerCase().includes(searchTerm.toLowerCase()) ||
    code.descripcion.toLowerCase().includes(searchTerm.toLowerCase()) ||
    code.categoria.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Group codes by chapter
  const codesGroupedByChapter = filteredCodes.reduce((acc, code) => {
    const chapter = code.capitulo || obtener_capitulo_cie10(code.codigo);
    if (!acc[chapter]) {
      acc[chapter] = [];
    }
    acc[chapter].push(code);
    return acc;
  }, {});

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Códigos CIE-10 con Clasificación por Capítulos</h1>
      
      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar código, descripción o categoría..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Chapters */}
      <div className="space-y-6">
        {Object.entries(codesGroupedByChapter).map(([chapter, codes]) => (
          <div key={chapter} className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 bg-gray-50 border-b">
              <h2 className="text-lg font-semibold text-gray-900">{chapter}</h2>
              <p className="text-sm text-gray-600">{codes.length} código(s)</p>
            </div>
            <div className="p-6">
              <div className="grid gap-3">
                {codes.map(code => (
                  <div key={code.id} className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                    <div className="flex-shrink-0 w-20">
                      <span className="font-mono font-semibold text-indigo-600">{code.codigo}</span>
                    </div>
                    <div className="flex-1 ml-4">
                      <p className="text-sm text-gray-900 font-medium">{code.descripcion}</p>
                      <p className="text-xs text-gray-500">{code.categoria}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Helper function for chapter classification
function obtener_capitulo_cie10(codigo) {
  if (!codigo) return "No clasificado";
  
  const primera_letra = codigo[0].toUpperCase();
  
  const capitulos = {
    'A': "Capítulo I – Ciertas enfermedades infecciosas y parasitarias (A00-B99)",
    'B': "Capítulo I – Ciertas enfermedades infecciosas y parasitarias (A00-B99)",
    'C': "Capítulo II – Neoplasias (C00-D48)",
    'D': "Capítulo III – Enfermedades de la sangre y órganos hematopoyéticos (D50-D89)",
    'E': "Capítulo IV – Enfermedades endocrinas, nutricionales y metabólicas (E00-E90)",
    'F': "Capítulo V – Trastornos mentales y del comportamiento (F00-F99)",
    'G': "Capítulo VI – Enfermedades del sistema nervioso (G00-G99)",
    'H': "Capítulo VII – Enfermedades del ojo y del oído (H00-H95)",
    'I': "Capítulo IX – Enfermedades del sistema circulatorio (I00-I99)",
    'J': "Capítulo X – Enfermedades del sistema respiratorio (J00-J99)",
    'K': "Capítulo XI – Enfermedades del sistema digestivo (K00-K93)",
    'L': "Capítulo XII – Enfermedades de la piel y tejido subcutáneo (L00-L99)",
    'M': "Capítulo XIII – Enfermedades del sistema osteomuscular (M00-M99)",
    'N': "Capítulo XIV – Enfermedades del sistema genitourinario (N00-N99)",
    'O': "Capítulo XV – Embarazo, parto y puerperio (O00-O99)",
    'P': "Capítulo XVI – Ciertas afecciones originadas en el período perinatal (P00-P96)",
    'Q': "Capítulo XVII – Malformaciones congénitas (Q00-Q99)",
    'R': "Capítulo XVIII – Síntomas, signos y hallazgos anormales (R00-R99)",
    'S': "Capítulo XIX – Traumatismos, envenenamientos (S00-T98)",
    'T': "Capítulo XIX – Traumatismos, envenenamientos (S00-T98)",
    'V': "Capítulo XX – Causas externas de morbilidad y mortalidad (V01-Y98)",
    'W': "Capítulo XX – Causas externas de morbilidad y mortalidad (V01-Y98)",
    'X': "Capítulo XX – Causas externas de morbilidad y mortalidad (V01-Y98)",
    'Y': "Capítulo XX – Causas externas de morbilidad y mortalidad (V01-Y98)",
    'Z': "Capítulo XXI – Factores que influyen en el estado de salud (Z00-Z99)"
  };
  
  return capitulos[primera_letra] || "No clasificado";
}

// Main App Component
function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [role, setRole] = useState(localStorage.getItem('role'));

  useEffect(() => {
    if (token) {
      setIsAuthenticated(true);
    }
  }, [token]);

  const handleLogin = (newToken, newRole) => {
    localStorage.setItem('token', newToken);
    localStorage.setItem('role', newRole);
    setToken(newToken);
    setRole(newRole);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    setToken(null);
    setRole(null);
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  return <Dashboard token={token} role={role} onLogout={handleLogout} />;
}

export default App;