import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import $ from "jquery";

class Blockcount extends Component {
  constructor(props) {
    super(props);
    this.state = {
      'length': '-',
      'known_length': '-'
    }
  }

  componentWillMount() {
    this.update();
  }

  update() {
    $.get("/blockcount", (data) => {
      this.setState((state) => {
        state['length'] = data.length;
        state['known_length'] = data.known_length;
        return state;
      });
    });
  }

  render() {
    let content = 'Loading';
    if(this.state.length !== '-') {
      content = this.state.length + '/' + this.state.known_length;
    }
    return (
      <div className="col-lg-3 col-md-6 col-sm-6">
        <MCardStats color="orange" header_icon="content_copy" title="Block Count"
         content={content} 
         footer_icon="update" alt_text="Just Updated"/>
      </div>
    );
  }
}

export default Blockcount;