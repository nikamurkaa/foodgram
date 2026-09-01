import ReactDOM from 'react-dom';

const MetaTags = ({ children }) => ReactDOM.createPortal(children, document.head);

export default MetaTags;
